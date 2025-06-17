from flask import jsonify

from activity import create_activity_user_log
from models import db, User, Domain, EventType


def get_users(current_user=None):
    # If no user is provided, try to get from JWT token
    if not current_user:
        from cognito import get_user_from_token
        success, user_data = get_user_from_token()
        if success:
            user_email = user_data.get("email")
            current_user = User.query.filter_by(email=user_email).first()

    if not current_user:
        return jsonify({"error": "No autorizado"}), 401

    # Check if user is admin
    if not current_user.is_admin:
        return jsonify({"error": "Acceso denegado. Se requieren permisos de administrador."}), 403

    users = User.query.all()
    domains = Domain.query.all()

    return jsonify({
        'users': [user.to_dict() for user in users],
        'domains': [domain.to_dict() for domain in domains]
    })

def get_user(user_id, current_user=None):
    # If no user is provided, try to get from JWT token
    if not current_user:
        from cognito import get_user_from_token
        success, user_data = get_user_from_token()
        if success:
            user_email = user_data.get("email")
            current_user = User.query.filter_by(email=user_email).first()

    if not current_user:
        return jsonify({"error": "No autorizado"}), 401

    # Check if user is admin
    if not current_user.is_admin:
        return jsonify({"error": "Acceso denegado. Se requieren permisos de administrador."}), 403

    user = User.query.get(user_id)
    if user:
        return jsonify(user.to_dict())

    return jsonify({"error": "Usuario no encontrado"}), 404

def create_user(data, current_user=None):
    print(f"[DEBUG] create_user called with data: {data}")
    
    # If no user is provided, try to get from JWT token
    if not current_user:
        print("[DEBUG] No current_user provided, trying to get from JWT token")
        from cognito import get_user_from_token
        success, user_data = get_user_from_token()
        if success:
            user_email = user_data.get("email")
            current_user = User.query.filter_by(email=user_email).first()
            print(f"[DEBUG] Got user from token: {user_email}, found in DB: {current_user is not None}")
        else:
            print(f"[DEBUG] Failed to get user from token: {user_data}")

    if not current_user:
        print("[DEBUG] No current user found, returning 401")
        return jsonify({"error": "No autorizado"}), 401

    print(f"[DEBUG] Current user: {current_user.email}, is_admin: {current_user.is_admin}")

    # Check if user is admin
    if not current_user.is_admin:
        print("[DEBUG] User is not admin, returning 403")
        create_activity_user_log(EventType.PERMISSION_VIOLATION, current_user.id, None, message='User ' + current_user.email + ' has no permission to create another user!')
        return jsonify({"error": "Acceso denegado. Se requieren permisos de administrador."}), 403

    if not data or not data.get('email'):
        print("[DEBUG] No email provided in data")
        return jsonify({"error": "El email es requerido"}), 400

    email = data.get('email')
    print(f"[DEBUG] Creating user with email: {email}")
    
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        print(f"[DEBUG] User with email {email} already exists")
        return jsonify({"error": "El email ya está en uso"}), 400

    try:
        domain_part = email.split('@')[1]
        print(f"[DEBUG] Domain part extracted: {domain_part}")
    except (IndexError, AttributeError) as e:
        print(f"[DEBUG] Failed to extract domain from email: {e}")
        return jsonify({"error": "invalid_email_error"}), 400

    allowed_domains = Domain.query.all()
    print(f"[DEBUG] Found {len(allowed_domains)} domains in database")
    
    domain_list = []
    for domain in allowed_domains:
        domain_name = domain.name
        if domain_name.startswith('@'):
            domain_list.append(domain_name[1:])
        else:
            domain_list.append(domain_name)
    
    print(f"[DEBUG] Allowed domains: {domain_list}")

    if not domain_list:
        print("[DEBUG] No allowed domains configured")
        return jsonify({"error": "no_allowed_domains_error"}), 400

    if domain_part not in domain_list:
        print(f"[DEBUG] Domain {domain_part} not in allowed list")
        return jsonify({"error": "domain_not_allowed_error", "domain": domain_part}), 400

    print("[DEBUG] Domain validation passed, proceeding to Cognito creation")

    # Create user in Cognito first
    from cognito import create_cognito_user
    import secrets
    import string
    
    # Generate a temporary password that meets Cognito policy requirements
    # Cognito typically requires: uppercase, lowercase, numbers, and symbols
    uppercase = string.ascii_uppercase
    lowercase = string.ascii_lowercase
    digits = string.digits
    symbols = '!@#$%^&*()_+-=[]{}|;:,.<>?'
    
    # Ensure at least one character from each required category
    temp_password = (
        secrets.choice(uppercase) +
        secrets.choice(lowercase) +
        secrets.choice(digits) +
        secrets.choice(symbols) +
        ''.join(secrets.choice(uppercase + lowercase + digits + symbols) for _ in range(8))
    )
    
    # Shuffle the password to randomize character positions
    temp_password_list = list(temp_password)
    secrets.SystemRandom().shuffle(temp_password_list)
    temp_password = ''.join(temp_password_list)
    
    print(f"[DEBUG] Generated temporary password: {temp_password[:4]}... (length: {len(temp_password)})")
    
    # Don't pass custom attributes since they don't exist in the Cognito schema
    # Database will be the source of truth for all permissions and roles
    print("[DEBUG] Skipping custom attributes - using database as source of truth for permissions")
    
    # Create user in Cognito
    print("[DEBUG] Calling create_cognito_user...")
    cognito_success, cognito_response = create_cognito_user(email, temp_password, user_attributes=None)
    print(f"[DEBUG] Cognito creation result: success={cognito_success}, response={cognito_response}")
    
    if not cognito_success:
        print(f"[ERROR] Cognito user creation failed: {cognito_response}")
        return jsonify({"error": f"Failed to create user in Cognito: {cognito_response.get('error', 'Unknown error')}"}), 500

    print("[DEBUG] Cognito user created successfully, creating database user...")

    # Create user in database
    new_user = User(
        email=email,
        chat_access=data.get('chatAccess', False),
        is_admin=data.get('isAdmin', False),
        is_catalog_editor=data.get('isCatalogEditor', False),
        role="admin" if data.get('isAdmin', False) else "user"
    )
    print(f"[DEBUG] Created User object: {new_user.email}")

    try:
        print("[DEBUG] Adding user to database session...")
        db.session.add(new_user)
        print("[DEBUG] Committing database transaction...")
        db.session.commit()
        print(f"[DEBUG] User {email} successfully created in database with ID: {new_user.id}")
        
        create_activity_user_log(EventType.USER_CREATION, current_user.id, new_user.id, 'User ' + current_user.email + ' created the user ' + email)
        
        # Return user data with temporary password for admin to share
        user_response = new_user.to_dict()
        user_response['temporary_password'] = temp_password
        print(f"[DEBUG] Returning successful response for user: {email}")
        return jsonify(user_response), 201
        
    except Exception as e:
        print(f"[ERROR] Database error during user creation: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        
        db.session.rollback()
        print("[DEBUG] Database transaction rolled back")
        
        # If database creation fails, clean up Cognito user
        print("[DEBUG] Attempting to clean up Cognito user...")
        from cognito import delete_cognito_user
        cleanup_success, cleanup_response = delete_cognito_user(email)
        if not cleanup_success:
            print(f"[ERROR] Failed to clean up Cognito user after database error: {cleanup_response}")
        else:
            print("[DEBUG] Cognito user cleanup successful")
        
        return jsonify({"error": "Error al crear usuario en la base de datos"}), 500

def update_user(user_id, data, current_user=None):
    # If no user is provided, try to get from JWT token
    if not current_user:
        from cognito import get_user_from_token
        success, user_data = get_user_from_token()
        if success:
            user_email = user_data.get("email")
            current_user = User.query.filter_by(email=user_email).first()

    if not current_user:
        return jsonify({"error": "No autorizado"}), 401

    # Check if user is admin
    if not current_user.is_admin:
        return jsonify({"error": "Acceso denegado. Se requieren permisos de administrador."}), 403

    if not data:
        return jsonify({"error": "No se proporcionaron datos"}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404

    # Track changes for Cognito synchronization
    cognito_updates = {}
    
    if 'email' in data:
        user.email = data['email']

    if 'documentAccess' in data:
        user.document_access = data['documentAccess']

    if 'chatAccess' in data:
        user.chat_access = data['chatAccess']
        cognito_updates['custom:chatAccess'] = data['chatAccess']

    if 'isAdmin' in data:
        user.is_admin = data['isAdmin']
        user.role = 'admin' if data['isAdmin'] else 'user'
        cognito_updates['custom:isAdmin'] = data['isAdmin']
        cognito_updates['custom:role'] = user.role

    if 'isCatalogEditor' in data:
        user.is_catalog_editor = data['isCatalogEditor']
        cognito_updates['custom:isCatalogEditor'] = data['isCatalogEditor']

    # Skip Cognito attribute updates - database is source of truth for permissions
    if cognito_updates:
        print(f"[DEBUG] Skipping Cognito attribute sync: {cognito_updates} - database is source of truth")

    try:
        db.session.commit()
        create_activity_user_log(EventType.USER_EDITION, current_user.id, user.id, 'User ' + current_user.email + ' edited the user ' + user.email + str(user))
        return jsonify(user.to_dict())
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Database error during user update: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        return jsonify({"error": "Error al actualizar usuario en la base de datos"}), 500

def toggle_user_property(user_id, property, current_user=None):
    # If no user is provided, try to get from JWT token
    if not current_user:
        from cognito import get_user_from_token
        success, user_data = get_user_from_token()
        if success:
            user_email = user_data.get("email")
            current_user = User.query.filter_by(email=user_email).first()

    if not current_user:
        return jsonify({"error": "No autorizado"}), 401

    # Check if user is admin
    if not current_user.is_admin:
        return jsonify({"error": "Acceso denegado. Se requieren permisos de administrador."}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404

    # Prevent admin from removing their own admin rights
    if property == 'isAdmin' and user.id == current_user.id and user.is_admin:
        return jsonify({"error": "cannot_remove_own_admin"}), 403

    allowed_properties = {
        'isAdmin': 'is_admin',
        'isCatalogEditor': 'is_catalog_editor',
        'chatAccess': 'chat_access'
    }

    if property not in allowed_properties:
        return jsonify({"error": f"Propiedad '{property}' no válida"}), 400

    db_property = allowed_properties[property]
    current_value = getattr(user, db_property)
    new_value = not current_value
    setattr(user, db_property, new_value)

    # Prepare Cognito updates
    cognito_updates = {}
    
    if property == 'isAdmin':
        user.role = 'admin' if new_value else 'user'
        cognito_updates['custom:isAdmin'] = new_value
        cognito_updates['custom:role'] = user.role
    elif property == 'isCatalogEditor':
        cognito_updates['custom:isCatalogEditor'] = new_value
    elif property == 'chatAccess':
        cognito_updates['custom:chatAccess'] = new_value

    # Skip Cognito attribute updates - database is source of truth for permissions
    if cognito_updates:
        print(f"[DEBUG] Skipping Cognito attribute sync: {cognito_updates} - database is source of truth")

    try:
        db.session.commit()
        create_activity_user_log(EventType.USER_EDITION, current_user.id, None, 'User ' + current_user.email +
             ' edited the user ' + str(user.id) + ' property ' + property)
        return jsonify(user.to_dict())
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Database error during user property toggle: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Error al cambiar propiedad de usuario: {str(e)}"}), 500

def delete_user(user_id, current_user=None):
    # If no user is provided, try to get from JWT token
    if not current_user:
        from cognito import get_user_from_token
        success, user_data = get_user_from_token()
        if success:
            user_email = user_data.get("email")
            current_user = User.query.filter_by(email=user_email).first()

    if not current_user:
        return jsonify({"error": "No autorizado"}), 401

    # Check if user is admin
    if not current_user.is_admin:
        create_activity_user_log(EventType.USER_PERMISSION, current_user.id, user_id, 'User ' + current_user.email +
                                 ' tried to delete the user ' + str(user_id))
        return jsonify({"error": "Acceso denegado. Se requieren permisos de administrador."}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404

    # Delete user from Cognito first
    from cognito import delete_cognito_user
    cognito_success, cognito_response = delete_cognito_user(user.email)
    
    if not cognito_success:
        # If user doesn't exist in Cognito, log it but continue with database deletion
        if "User not found in Cognito" not in cognito_response.get('error', ''):
            return jsonify({"error": f"Failed to delete user from Cognito: {cognito_response.get('error', 'Unknown error')}"}), 500
        else:
            print(f"Warning: User {user.email} not found in Cognito, continuing with database deletion")

    try:
        deleted_user = user.to_dict()
        db.session.delete(user)
        db.session.commit()
        create_activity_user_log(EventType.USER_DELETION, current_user.id, user_id, 'User ' + current_user.email +
             ' deleted the user ' + str(user.id))
        return jsonify({"success": True, "eliminado": deleted_user})
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Database error during user deletion: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        
        # If database deletion fails but Cognito deletion succeeded, we should try to restore Cognito user
        # For now, just log the error as this is a complex rollback scenario
        print(f"[WARNING] User {user.email} was deleted from Cognito but database deletion failed")
        
        return jsonify({"error": "Error al eliminar usuario de la base de datos"}), 500
