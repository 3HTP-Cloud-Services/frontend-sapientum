from flask import session, request, jsonify
from models import db, User, Domain

def get_users():
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401

    # Check if user is admin
    user_email = session.get('user_email')
    user = User.query.filter_by(email=user_email).first()
    if not user or not user.is_admin:
        return jsonify({"error": "Acceso denegado. Se requieren permisos de administrador."}), 403

    users = User.query.all()
    domains = Domain.query.all()

    return jsonify({
        'users': [user.to_dict() for user in users],
        'domains': [domain.to_dict() for domain in domains]
    })

def get_user(user_id):
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401

    # Check if user is admin
    user_email = session.get('user_email')
    current_user = User.query.filter_by(email=user_email).first()
    if not current_user or not current_user.is_admin:
        return jsonify({"error": "Acceso denegado. Se requieren permisos de administrador."}), 403

    user = User.query.get(user_id)
    if user:
        return jsonify(user.to_dict())

    return jsonify({"error": "Usuario no encontrado"}), 404

def create_user(data):
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401

    # Check if user is admin
    user_email = session.get('user_email')
    current_user = User.query.filter_by(email=user_email).first()
    if not current_user or not current_user.is_admin:
        return jsonify({"error": "Acceso denegado. Se requieren permisos de administrador."}), 403

    if not data or not data.get('email'):
        return jsonify({"error": "El email es requerido"}), 400

    email = data.get('email')
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"error": "El email ya está en uso"}), 400

    try:
        domain_part = email.split('@')[1]
    except (IndexError, AttributeError):
        return jsonify({"error": "invalid_email_error"}), 400

    allowed_domains = Domain.query.all()
    domain_list = []
    for domain in allowed_domains:
        domain_name = domain.name
        if domain_name.startswith('@'):
            domain_list.append(domain_name[1:])
        else:
            domain_list.append(domain_name)

    if not domain_list:
        return jsonify({"error": "no_allowed_domains_error"}), 400

    if domain_part not in domain_list:
        return jsonify({"error": "domain_not_allowed_error", "domain": domain_part}), 400

    new_user = User(
        email=email,
        chat_access=data.get('chatAccess', False),
        is_admin=data.get('isAdmin', False),
        role="admin" if data.get('isAdmin', False) else "user"
    )

    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify(new_user.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error creating user: {e}")
        return jsonify({"error": "Error al crear usuario en la base de datos"}), 500

def update_user(user_id, data):
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401

    # Check if user is admin
    user_email = session.get('user_email')
    current_user = User.query.filter_by(email=user_email).first()
    if not current_user or not current_user.is_admin:
        return jsonify({"error": "Acceso denegado. Se requieren permisos de administrador."}), 403

    if not data:
        return jsonify({"error": "No se proporcionaron datos"}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404

    if 'email' in data:
        user.email = data['email']

    if 'documentAccess' in data:
        user.document_access = data['documentAccess']

    if 'chatAccess' in data:
        user.chat_access = data['chatAccess']

    if 'isAdmin' in data:
        user.is_admin = data['isAdmin']
        user.role = 'admin' if data['isAdmin'] else 'user'

    if 'isCatalogEditor' in data:
        user.is_catalog_editor = data['isCatalogEditor']

    try:
        db.session.commit()
        return jsonify(user.to_dict())
    except Exception as e:
        db.session.rollback()
        print(f"Error updating user: {e}")
        return jsonify({"error": "Error al actualizar usuario en la base de datos"}), 500

def toggle_user_property(user_id, property):
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401

    # Check if user is admin
    user_email = session.get('user_email')
    current_user = User.query.filter_by(email=user_email).first()
    if not current_user or not current_user.is_admin:
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
    setattr(user, db_property, not current_value)

    # Update role if changing admin status
    if property == 'isAdmin':
        user.role = 'admin' if not current_value else 'user'

    try:
        db.session.commit()
        return jsonify(user.to_dict())
    except Exception as e:
        db.session.rollback()
        print(f"Error toggling user property: {e}")
        return jsonify({"error": f"Error al cambiar propiedad de usuario: {str(e)}"}), 500

def delete_user(user_id):
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401

    # Check if user is admin
    user_email = session.get('user_email')
    current_user = User.query.filter_by(email=user_email).first()
    if not current_user or not current_user.is_admin:
        return jsonify({"error": "Acceso denegado. Se requieren permisos de administrador."}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404

    try:
        deleted_user = user.to_dict()
        db.session.delete(user)
        db.session.commit()
        return jsonify({"success": True, "eliminado": deleted_user})
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting user: {e}")
        return jsonify({"error": "Error al eliminar usuario de la base de datos"}), 500