from models import db, ActivityLog, EventType, Catalog, File
from datetime import datetime
from flask import request, jsonify

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

def create_activity_log_message(event, user_email, catalog_id, message_id, activity, message):
    try:
        activity_log = ActivityLog(
            activity=activity,
            message=message,
            event=event,
            user_email=user_email,
            catalog_id=catalog_id,
            message_id=message_id,
            created_at=datetime.now()
        )
        db.session.add(activity_log)
        db.session.commit()
        print(f"Activity log created: Event {event}, User {user_email} in catalog {catalog_id} in message {message_id}: {activity}")
        return True
    except Exception as e:
        print(f"Error creating activity log: {e}")
        return False

def get_activity_logs_with_pagination():
    """Get activity logs with pagination and formatting"""
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        # Ensure per_page is within reasonable limits
        per_page = min(per_page, 100)

        # Get paginated activity logs, ordered by creation time (newest first)
        pagination = ActivityLog.query.order_by(ActivityLog.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        logs = pagination.items

        # Convert logs to dictionaries with user email
        formatted_logs = []
        for log in logs:
            log_dict = log.to_dict()

            # Add catalog name if present
            if log.catalog_id:
                catalog = db.session.get(Catalog, log.catalog_id)
                if catalog:
                    log_dict['catalog_name'] = catalog.name

            # Add file name if present
            if log.file_id:
                file = db.session.get(File, log.file_id)
                if file:
                    log_dict['file_name'] = file.name

            formatted_logs.append(log_dict)

        return jsonify({
            "logs": formatted_logs,
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total": pagination.total,
                "pages": pagination.pages,
                "has_prev": pagination.has_prev,
                "has_next": pagination.has_next
            }
        })
    except Exception as e:
        print(f"Error fetching activity logs: {e}")
        return jsonify({"error": "Error al cargar registros de actividad"}), 500
