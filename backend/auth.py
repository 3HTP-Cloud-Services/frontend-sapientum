from botocore.exceptions import ClientError
from aws_utils import get_dynamodb_table
import traceback

def authenticate_user(email, password):
    max_retries = 2
    for attempt in range(max_retries):
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
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'ExpiredToken' and attempt < max_retries - 1:
                print(f"Token expired, retrying... (attempt {attempt+1}/{max_retries})")
                continue
            elif error_code == 'ExpiredToken':
                print(f"Token still expired after {max_retries} attempts: {e}")
                traceback.print_exc()
                return None, "Authentication error (token expired)"
            else:
                print(f"Error authenticating user {email}: {e}")
                traceback.print_exc()
                return None, "Authentication error"
        except Exception as e:
            print(f"Unexpected error: {e}")
            traceback.print_exc()
            return None, "Authentication error"


def get_user_role(email):
    max_retries = 2
    for attempt in range(max_retries):
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
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'ExpiredToken' and attempt < max_retries - 1:
                print(f"Token expired, retrying... (attempt {attempt+1}/{max_retries})")
                continue
            elif error_code == 'ExpiredToken':
                print(f"Token still expired after {max_retries} attempts: {e}")
                traceback.print_exc()
                return None
            else:
                print(f"Error getting role for user {email}: {e}")
                traceback.print_exc()
                return None
        except Exception as e:
            print(f"Unexpected error getting role: {e}")
            traceback.print_exc()
            return None


def get_all_users():
    max_retries = 2
    for attempt in range(max_retries):
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
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'ExpiredToken' and attempt < max_retries - 1:
                print(f"Token expired, retrying... (attempt {attempt+1}/{max_retries})")
                continue
            elif error_code == 'ExpiredToken':
                print(f"Token still expired after {max_retries} attempts: {e}")
                traceback.print_exc()
                return []
            else:
                print(f"Error getting users: {e}")
                traceback.print_exc()
                return []
        except Exception as e:
            print(f"Unexpected error getting users: {e}")
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
    max_retries = 2
    for attempt in range(max_retries):
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
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'ExpiredToken' and attempt < max_retries - 1:
                print(f"Token expired, retrying... (attempt {attempt+1}/{max_retries})")
                continue
            elif error_code == 'ExpiredToken':
                print(f"Token still expired after {max_retries} attempts: {e}")
                traceback.print_exc()
                return False
            else:
                print(f"Error updating user in DynamoDB: {e}")
                traceback.print_exc()
                return False
        except Exception as e:
            print(f"Unexpected error updating user: {e}")
            traceback.print_exc()
            return False


def create_user_in_dynamo(user_data):
    max_retries = 2
    for attempt in range(max_retries):
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
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'ExpiredToken' and attempt < max_retries - 1:
                print(f"Token expired, retrying... (attempt {attempt+1}/{max_retries})")
                continue
            elif error_code == 'ExpiredToken':
                print(f"Token still expired after {max_retries} attempts: {e}")
                traceback.print_exc()
                return False
            else:
                print(f"Error creating user in DynamoDB: {e}")
                traceback.print_exc()
                return False
        except Exception as e:
            print(f"Unexpected error creating user: {e}")
            traceback.print_exc()
            return False


def delete_user_from_dynamo(username):
    max_retries = 2
    for attempt in range(max_retries):
        try:
            table = get_dynamodb_table('sapientum_people')
            table.delete_item(
                Key={
                    'username': username
                }
            )
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'ExpiredToken' and attempt < max_retries - 1:
                print(f"Token expired, retrying... (attempt {attempt+1}/{max_retries})")
                continue
            elif error_code == 'ExpiredToken':
                print(f"Token still expired after {max_retries} attempts: {e}")
                traceback.print_exc()
                return False
            else:
                print(f"Error deleting user from DynamoDB: {e}")
                traceback.print_exc()
                return False
        except Exception as e:
            print(f"Unexpected error deleting user: {e}")
            traceback.print_exc()
            return False