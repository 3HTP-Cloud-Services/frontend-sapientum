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

        # Extract tokens
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
