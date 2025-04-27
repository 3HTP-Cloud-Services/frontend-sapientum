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
        traceback.print_exc()
        return None, "Authentication error"
    except Exception as e:
        print(f"Unexpected error: {e}")
        print("Full stack trace:")
        traceback.print_exc()
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


def get_all_users():
    try:
        table = get_dynamodb_table('sapientum_people')
        response = table.scan()
        users = response.get('Items', [])
        
        formatted_users = []
        for idx, user in enumerate(users, start=1):
            formatted_users.append({
                'id': idx,
                'username': user.get('username', ''),
                'isAdmin': user.get('role') == 'admin',
                'role': user.get('role', 'user')
            })
            
        return formatted_users
    except ClientError as e:
        print(f"Error getting users: {e}")
        traceback.print_exc()
        return []


def get_user_by_id(user_id, users_list=None):
    if users_list is None:
        users_list = get_all_users()
        
    for user in users_list:
        if user['id'] == user_id:
            return user
    return None


def update_user_in_dynamo(user_data):
    try:
        original_username = user_data.get('original_username')
        new_username = user_data.get('email')
        new_role = 'admin' if user_data.get('isAdmin') else 'user'
        
        table = get_dynamodb_table('sapientum_people')
        
        if original_username != new_username:
            table.delete_item(
                Key={
                    'username': original_username
                }
            )
            
            table.put_item(
                Item={
                    'username': new_username,
                    'role': new_role
                }
            )
        else:
            table.update_item(
                Key={
                    'username': original_username
                },
                UpdateExpression="set #r = :r",
                ExpressionAttributeNames={
                    '#r': 'role'
                },
                ExpressionAttributeValues={
                    ':r': new_role
                }
            )
            
        return True
    except ClientError as e:
        print(f"Error updating user in DynamoDB: {e}")
        traceback.print_exc()
        return False


def create_user_in_dynamo(user_data):
    try:
        username = user_data.get('email')
        role = 'admin' if user_data.get('isAdmin') else 'user'
        
        table = get_dynamodb_table('sapientum_people')
        table.put_item(
            Item={
                'username': username,
                'role': role
            }
        )
        return True
    except ClientError as e:
        print(f"Error creating user in DynamoDB: {e}")
        traceback.print_exc()
        return False


def delete_user_from_dynamo(username):
    try:
        table = get_dynamodb_table('sapientum_people')
        table.delete_item(
            Key={
                'username': username
            }
        )
        return True
    except ClientError as e:
        print(f"Error deleting user from DynamoDB: {e}")
        traceback.print_exc()
        return False