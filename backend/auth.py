from botocore.exceptions import ClientError
from sqlalchemy.event import Events

import traceback

from activity import create_activity_user_log
from models import EventType
from models import User

def authenticate_user(email, password):
    def operation():
        user = User.query.filter_by(email=email).first()

        if not user:
            return None, "Unknown User"

        # Hardcoded password for development
        stored_password = 'user123'

        if stored_password == password:
            create_activity_user_log(EventType.USER_LOGIN, user.id, None, 'User ' + email + ' logged in')
            return user.to_dict(), None
        else:
            return None, "Invalid credentials"

    try:
        return operation()
    except ClientError as e:
        print(f"Error authenticating user {email}: {e}")
        traceback.print_exc()
        return None, "Authentication error"
    except Exception as e:
        print(f"Unexpected error: {e}")
        traceback.print_exc()
        return None, "Authentication error"

def get_all_domains():
    return ['@3htp.com', '@3htp.cloud']
