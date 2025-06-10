import boto3
import json
import os
from flask import jsonify

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
