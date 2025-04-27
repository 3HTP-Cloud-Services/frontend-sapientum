from botocore.exceptions import ClientError
from aws_utils import get_dynamodb_table
import traceback

def authenticate_user(email, password):
    try:
        table = get_dynamodb_table('sapientum_people')
        response = table.get_item(
            Key={
                'username': email,
            }
        )
        
        user = response.get('Item')
        
        if not user:
            return None, "Unknown User"
            
        stored_password = 'user123' #user.get('password')
        
        if stored_password == password:
            return user, None
        else:
            return None, "Invalid credentials"

    except ClientError as e:
        print(f"Error authenticating user {email}: {e}")
        print("Full stack trace:")
        traceback.print_exc()  # This will print the full stack trace
        return None, "Authentication error"
    except Exception as e:
        print(f"Unexpected error: {e}")
        print("Full stack trace:")
        traceback.print_exc()  # Also catch other exceptions
        return None, "Authentication error"


def get_user_role(email):
    try:
        table = get_dynamodb_table('sapientum_people')
        response = table.get_item(
            Key={
                'username': email
            }
        )
        
        user = response.get('Item')
        if user:
            return user.get('role')
        return None
        
    except ClientError as e:
        print(f"Error getting role for user {email}: {e}")
        return None