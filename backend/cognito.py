import boto3
import json
import os
import jwt
import requests
from jwt import PyJWKClient
from flask import jsonify, request

def get_cognito_client():
    """Get Cognito client instance"""
    return boto3.client('cognito-idp')

def authenticate_user(username, password):
    """
    Authenticate user with AWS Cognito
    Returns a tuple: (success, response_data)
    """
    try:
        client = get_cognito_client()

        # Get environment variables
        # For local development, you can hardcode these values
        if os.environ.get('FLASK_ENV') == 'development':
            user_pool_id = "us-east-1_1pPT6lSMc"
            client_id = "4ed15at0palqflefuvlu536mme"
        else:
            user_pool_id = os.environ.get('COGNITO_USER_POOL_ID')
            client_id = os.environ.get('COGNITO_CLIENT_ID')

        print('cognito1')
        if not user_pool_id or not client_id:
            return False, {"error": "Cognito configuration not found"}

        print('cognito2')
        # Initiate auth with Cognito
        auth_response = client.admin_initiate_auth(
            UserPoolId=user_pool_id,
            ClientId=client_id,
            AuthFlow='ADMIN_USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password
            }
        )
        print('cognito3', auth_response)

        # Check if this is a challenge response (like NEW_PASSWORD_REQUIRED)
        if 'ChallengeName' in auth_response:
            challenge_name = auth_response['ChallengeName']
            if challenge_name == 'NEW_PASSWORD_REQUIRED':
                return False, {
                    "error": "new_password_required",
                    "challenge": challenge_name,
                    "session": auth_response.get('Session', ''),
                    "message": "New password required",
                    "user_attributes": auth_response.get('ChallengeParameters', {}).get('userAttributes', '{}')
                }
            else:
                return False, {"error": f"Unhandled challenge: {challenge_name}", "response": str(auth_response)}

        # Extract tokens for successful authentication
        if 'AuthenticationResult' not in auth_response:
            return False, {"error": "Authentication failed", "response": str(auth_response)}

        auth_result = auth_response['AuthenticationResult']
        id_token = auth_result.get('IdToken', '')
        access_token = auth_result.get('AccessToken', '')
        refresh_token = auth_result.get('RefreshToken', '')
        expires_in = auth_result.get('ExpiresIn', 0)

        return True, {
            "message": "Login successful",
            "idToken": id_token,
            "accessToken": access_token,
            "refreshToken": refresh_token,
            "expiresIn": expires_in
        }

    except client.exceptions.NotAuthorizedException:
        return False, {"error": "Invalid username or password"}
    except client.exceptions.UserNotFoundException:
        return False, {"error": "User not found"}
    except client.exceptions.UserNotConfirmedException:
        return False, {"error": "User is not confirmed"}
    except client.exceptions.PasswordResetRequiredException:
        return False, {"error": "Password reset required"}
    except client.exceptions.NewPasswordRequiredException as e:
        # Return the session for password change completion
        return False, {
            "error": "New password required",
            "session": e.response.get('Session', ''),
            "message": "Use the /api/set-password endpoint to set a new password"
        }
    except Exception as e:
        print("unexpected error:", str(e))
        return False, {"error": str(e)}

def get_cognito_config():
    """Get Cognito configuration"""
    if os.environ.get('FLASK_ENV') == 'development':
        user_pool_id = "us-east-1_1pPT6lSMc"
        client_id = "4ed15at0palqflefuvlu536mme"
    else:
        user_pool_id = os.environ.get('COGNITO_USER_POOL_ID')
        client_id = os.environ.get('COGNITO_CLIENT_ID')
    
    return user_pool_id, client_id

def verify_jwt_token(token):
    """
    Verify JWT token from Cognito
    Returns tuple: (success, user_data)
    """
    try:
        user_pool_id, client_id = get_cognito_config()
        
        if not user_pool_id or not client_id:
            return False, {"error": "Cognito configuration not found"}
        
        # Get the region from user pool id
        region = user_pool_id.split('_')[0]
        
        # Construct the JWK URL
        jwk_url = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json"
        
        # Create JWK client
        jwk_client = PyJWKClient(jwk_url)
        
        # Get the signing key
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        
        # Decode and verify the token
        decoded_token = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=client_id,
            issuer=f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}"
        )
        
        return True, decoded_token
        
    except jwt.ExpiredSignatureError:
        return False, {"error": "Token has expired"}
    except jwt.InvalidTokenError:
        return False, {"error": "Invalid token"}
    except Exception as e:
        print(f"Token verification error: {str(e)}")
        return False, {"error": f"Token verification failed: {str(e)}"}

def create_cognito_user(email, temporary_password, user_attributes=None):
    """
    Create a new user in Cognito
    Returns tuple: (success, response_data)
    """
    print(f"[DEBUG] create_cognito_user called for email: {email}")
    
    try:
        print("[DEBUG] Getting Cognito client...")
        client = get_cognito_client()
        user_pool_id, client_id = get_cognito_config()
        print(f"[DEBUG] Cognito config - pool_id: {user_pool_id}, client_id: {client_id}")
        
        if not user_pool_id:
            print("[ERROR] No user pool ID found in configuration")
            return False, {"error": "Cognito configuration not found"}
        
        # Default user attributes
        attributes = [
            {
                'Name': 'email',
                'Value': email
            },
            {
                'Name': 'email_verified',
                'Value': 'true'
            }
        ]
        print(f"[DEBUG] Base attributes: {attributes}")
        
        # Add custom attributes if provided
        if user_attributes:
            print(f"[DEBUG] Adding custom attributes: {user_attributes}")
            for key, value in user_attributes.items():
                if key.startswith('custom:'):
                    attr_value = str(value).lower() if isinstance(value, bool) else str(value)
                    attributes.append({
                        'Name': key,
                        'Value': attr_value
                    })
                    print(f"[DEBUG] Added custom attribute: {key} = {attr_value}")
        
        print(f"[DEBUG] Final attributes list: {attributes}")
        print(f"[DEBUG] Calling admin_create_user with pool_id: {user_pool_id}")
        
        # Create user in Cognito
        # MessageAction omitted - will use default configured message
        response = client.admin_create_user(
            UserPoolId=user_pool_id,
            Username=email,
            UserAttributes=attributes,
            TemporaryPassword=temporary_password
        )
        
        print(f"[DEBUG] Cognito user creation successful: {response.get('User', {}).get('Username', 'unknown')}")
        return True, {
            "message": "User created successfully in Cognito",
            "user": response.get('User', {})
        }
        
    except client.exceptions.UsernameExistsException as e:
        print(f"[ERROR] Username already exists in Cognito: {str(e)}")
        return False, {"error": "User already exists in Cognito"}
    except client.exceptions.InvalidPasswordException as e:
        print(f"[ERROR] Invalid password format: {str(e)}")
        return False, {"error": "Invalid password format"}
    except Exception as e:
        print(f"[ERROR] Unexpected error creating Cognito user: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        return False, {"error": f"Failed to create user in Cognito: {str(e)}"}

def delete_cognito_user(email):
    """
    Delete a user from Cognito
    Returns tuple: (success, response_data)
    """
    print(f"[DEBUG] delete_cognito_user called for email: {email}")
    
    try:
        client = get_cognito_client()
        user_pool_id, client_id = get_cognito_config()
        print(f"[DEBUG] Cognito config - pool_id: {user_pool_id}, client_id: {client_id}")
        
        if not user_pool_id:
            print("[ERROR] No user pool ID found in configuration")
            return False, {"error": "Cognito configuration not found"}
        
        print(f"[DEBUG] Calling admin_delete_user with pool_id: {user_pool_id}")
        
        # Delete user from Cognito
        client.admin_delete_user(
            UserPoolId=user_pool_id,
            Username=email
        )
        
        print(f"[DEBUG] User {email} deleted successfully from Cognito")
        return True, {"message": "User deleted successfully from Cognito"}
        
    except client.exceptions.UserNotFoundException as e:
        print(f"[ERROR] User not found in Cognito: {str(e)}")
        return False, {"error": "User not found in Cognito"}
    except Exception as e:
        print(f"[ERROR] Unexpected error deleting Cognito user: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        return False, {"error": f"Failed to delete user from Cognito: {str(e)}"}

def update_cognito_user_attributes(email, user_attributes):
    """
    Update user attributes in Cognito
    Returns tuple: (success, response_data)
    """
    try:
        client = get_cognito_client()
        user_pool_id, client_id = get_cognito_config()
        
        if not user_pool_id:
            return False, {"error": "Cognito configuration not found"}
        
        # Build attributes list
        attributes = []
        for key, value in user_attributes.items():
            if key.startswith('custom:'):
                attributes.append({
                    'Name': key,
                    'Value': str(value).lower() if isinstance(value, bool) else str(value)
                })
        
        if attributes:
            client.admin_update_user_attributes(
                UserPoolId=user_pool_id,
                Username=email,
                UserAttributes=attributes
            )
        
        return True, {"message": "User attributes updated successfully in Cognito"}
        
    except client.exceptions.UserNotFoundException:
        return False, {"error": "User not found in Cognito"}
    except Exception as e:
        print(f"Error updating Cognito user attributes: {str(e)}")
        return False, {"error": f"Failed to update user attributes in Cognito: {str(e)}"}

def respond_to_auth_challenge(username, new_password, session):
    """
    Respond to NEW_PASSWORD_REQUIRED challenge
    Returns tuple: (success, response_data)
    """
    print(f"[DEBUG] respond_to_auth_challenge called for user: {username}")
    
    try:
        client = get_cognito_client()
        user_pool_id, client_id = get_cognito_config()
        
        if not user_pool_id or not client_id:
            print("[ERROR] No Cognito configuration found")
            return False, {"error": "Cognito configuration not found"}
        
        print(f"[DEBUG] Responding to NEW_PASSWORD_REQUIRED challenge")
        
        response = client.admin_respond_to_auth_challenge(
            UserPoolId=user_pool_id,
            ClientId=client_id,
            ChallengeName='NEW_PASSWORD_REQUIRED',
            ChallengeResponses={
                'USERNAME': username,
                'NEW_PASSWORD': new_password
            },
            Session=session
        )
        
        print(f"[DEBUG] Challenge response successful")
        
        # Extract tokens from successful response
        auth_result = response.get('AuthenticationResult', {})
        id_token = auth_result.get('IdToken', '')
        access_token = auth_result.get('AccessToken', '')
        refresh_token = auth_result.get('RefreshToken', '')
        expires_in = auth_result.get('ExpiresIn', 0)
        
        return True, {
            "message": "Password updated and login successful",
            "idToken": id_token,
            "accessToken": access_token,
            "refreshToken": refresh_token,
            "expiresIn": expires_in
        }
        
    except client.exceptions.InvalidPasswordException as e:
        print(f"[ERROR] Invalid password: {str(e)}")
        return False, {"error": "Password does not meet policy requirements"}
    except client.exceptions.NotAuthorizedException as e:
        print(f"[ERROR] Not authorized: {str(e)}")
        return False, {"error": "Invalid session or credentials"}
    except Exception as e:
        print(f"[ERROR] Unexpected error in challenge response: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        return False, {"error": f"Failed to update password: {str(e)}"}

def get_user_from_token():
    """
    Extract user information from Authorization header
    Returns tuple: (success, user_data)
    """
    auth_header = request.headers.get('Authorization')
    
    if not auth_header:
        return False, {"error": "No Authorization header"}
    
    if not auth_header.startswith('Bearer '):
        return False, {"error": "Invalid Authorization header format"}
    
    token = auth_header[7:]  # Remove 'Bearer ' prefix
    
    success, token_data = verify_jwt_token(token)
    
    if not success:
        return False, token_data
    
    # Extract user information from token
    user_info = {
        "email": token_data.get("email"),
        "user_id": token_data.get("sub"),
        "role": token_data.get("custom:role"),
        "is_admin": token_data.get("custom:isAdmin") == "true",
        "chat_access": token_data.get("custom:chatAccess") == "true",
        "doc_access": token_data.get("custom:docAccess")
    }
    
    return True, user_info

def forgot_password(username):
    """
    Initiate forgot password flow in Cognito
    Sends verification code to user's email
    Returns tuple: (success, response_data)
    """
    print(f"[DEBUG] forgot_password called for username: {username}")
    try:
        client = get_cognito_client()
        user_pool_id, client_id = get_cognito_config()
        
        if not user_pool_id or not client_id:
            return False, {"error": "Cognito configuration not found"}
        
        print(f"[DEBUG] Using user_pool_id: {user_pool_id}, client_id: {client_id}")
        
        # Check user status first
        success, user_data = get_user_status(username)
        if success:
            user_status = user_data.get('status')
            print(f"[DEBUG] User status before forgot password: {user_status}")
            
            # Check if user is in a state that prevents password reset
            if user_status == 'FORCE_CHANGE_PASSWORD':
                return False, {
                    "error": "You have a temporary password that must be changed. Please log in with your temporary password and set a new password."
                }
            elif user_status == 'EXTERNAL_PROVIDER':
                return False, {
                    "error": "Your account uses social login. Please use your social login provider to access your account."
                }
            elif user_status == 'UNCONFIRMED':
                return False, {
                    "error": "Your account is not confirmed. Please check your email for a confirmation link or contact support."
                }
        
        # Initiate forgot password
        print(f"[DEBUG] Calling client.forgot_password for username: {username}")
        response = client.forgot_password(
            ClientId=client_id,
            Username=username
        )
        
        return True, {
            "message": "Password reset code sent to your email",
            "destination": response.get('CodeDeliveryDetails', {}).get('Destination', '')
        }
        
    except client.exceptions.UserNotFoundException:
        return False, {"error": "User not found"}
    except client.exceptions.InvalidParameterException:
        return False, {"error": "Invalid parameter"}
    except client.exceptions.NotAuthorizedException as e:
        print(f"[ERROR] NotAuthorizedException in forgot_password: {e}")
        print(f"[ERROR] Full exception response: {e.response}")
        return False, {"error": f"User is not authorized: {str(e)}"}
    except client.exceptions.LimitExceededException:
        return False, {"error": "Too many requests. Please wait and try again"}
    except Exception as e:
        print(f"Error in forgot_password: {str(e)}")
        return False, {"error": f"Failed to send reset code: {str(e)}"}

def confirm_forgot_password(username, confirmation_code, new_password):
    """
    Confirm forgot password with verification code and set new password
    Returns tuple: (success, response_data)
    """
    print(f"[DEBUG] confirm_forgot_password called for username: {username}")
    try:
        client = get_cognito_client()
        user_pool_id, client_id = get_cognito_config()
        
        if not user_pool_id or not client_id:
            return False, {"error": "Cognito configuration not found"}
        
        # Confirm forgot password
        client.confirm_forgot_password(
            ClientId=client_id,
            Username=username,
            ConfirmationCode=confirmation_code,
            Password=new_password
        )
        
        return True, {"message": "Password reset successfully"}
        
    except client.exceptions.CodeMismatchException:
        return False, {"error": "Invalid verification code"}
    except client.exceptions.ExpiredCodeException:
        return False, {"error": "Verification code has expired"}
    except client.exceptions.InvalidPasswordException:
        return False, {"error": "Password does not meet policy requirements"}
    except client.exceptions.UserNotFoundException:
        return False, {"error": "User not found"}
    except client.exceptions.NotAuthorizedException as e:
        print(f"[ERROR] NotAuthorizedException in confirm_forgot_password: {e}")
        print(f"[ERROR] Full exception response: {e.response}")
        return False, {"error": f"User is not authorized: {str(e)}"}
    except client.exceptions.LimitExceededException:
        return False, {"error": "Too many attempts. Please wait and try again"}
    except Exception as e:
        print(f"Error in confirm_forgot_password: {str(e)}")
        return False, {"error": f"Failed to reset password: {str(e)}"}

def get_user_status(username):
    """
    Get user status from Cognito for debugging
    Returns tuple: (success, user_data)
    """
    try:
        client = get_cognito_client()
        user_pool_id, client_id = get_cognito_config()
        
        if not user_pool_id:
            return False, {"error": "Cognito configuration not found"}
        
        response = client.admin_get_user(
            UserPoolId=user_pool_id,
            Username=username
        )
        
        user_status = response.get('UserStatus')
        user_attributes = response.get('UserAttributes', [])
        enabled = response.get('Enabled', False)
        
        print(f"[DEBUG] User {username} status: {user_status}")
        print(f"[DEBUG] User enabled: {enabled}")
        print(f"[DEBUG] User attributes: {user_attributes}")
        
        return True, {
            "status": user_status,
            "enabled": enabled,
            "attributes": user_attributes
        }
        
    except client.exceptions.UserNotFoundException:
        return False, {"error": "User not found"}
    except Exception as e:
        print(f"Error getting user status: {str(e)}")
        return False, {"error": f"Failed to get user status: {str(e)}"}
