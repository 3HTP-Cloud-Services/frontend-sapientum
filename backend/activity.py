from models import db, ActivityLog, EventType
from datetime import datetime

def create_activity_user_log(event, user_email, other_user_email, activity):
    try:
        activity_log = ActivityLog(
            activity=activity,
            event=event,
            user_email=user_email,
            other_user_email=other_user_email,
            created_at=datetime.now()
        )
        db.session.add(activity_log)
        db.session.commit()
        print(f"Activity log created: Event {event}, User {user_email} edited user {other_user_email}: {activity}")
        return True
    except Exception as e:
        print(f"Error creating activity log: {e}")
        return False

def create_activity_catalog_log(event, user_email, catalog_id, activity):
    try:
        activity_log = ActivityLog(
            activity=activity,
            event=event,
            user_email=user_email,
            catalog_id=catalog_id,
            created_at=datetime.now()
        )
        db.session.add(activity_log)
        db.session.commit()
        print(f"Activity log created: Event {event}, User {user_email} edited catalog {catalog_id}: {activity}")
        return True
    except Exception as e:
        print(f"Error creating activity log: {e}")
        return False

def create_activity_chat_log(event, user_email, catalog_id, message_id, activity):
    try:
        activity_log = ActivityLog(
            activity=activity,
            event=event,
            user_email=user_email,
            catalog_id=catalog_id,
            message_id=message_id,
            created_at=datetime.now()
        )
        db.session.add(activity_log)
        db.session.commit()
        print(f"Activity log created: Event {event}, User {user_email} spoke on catalog {catalog_id}: {activity}")
        return True
    except Exception as e:
        print(f"Error creating activity log: {e}")
        return False

def create_activity_log_message(event, user_id, catalog_id, message_id, activity, message):
    try:
        activity_log = ActivityLog(
            activity=activity,
            message=message,
            event=event,
            user_id=user_id,
            catalog_id=catalog_id,
            message_id=message_id,
            created_at=datetime.now()
        )
        db.session.add(activity_log)
        db.session.commit()
        print(f"Activity log created: Event {event}, User {user_id} in catalog {catalog_id} in message {message_id}: {activity}")
        return True
    except Exception as e:
        print(f"Error creating activity log: {e}")
        return False
