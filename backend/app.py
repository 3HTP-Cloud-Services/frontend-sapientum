from flask import Flask, request, jsonify, send_from_directory, send_file, Response
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
import json
from models import db, User, Domain, Catalog, File, Version, ActivityLog, EventType
import db as db_utils
import traceback
from datetime import datetime
from werkzeug.local import LocalProxy
from chat import generate_ai_response
from activity import create_activity_chat_log
from urllib.parse import quote
from auth_decorator import token_required, admin_required, chat_access_required, catalog_admin_required
from botocore.exceptions import ClientError
import re
import unicodedata

from catalog import get_all_catalogs

current_dir = os.path.dirname(os.path.abspath(__file__))
static_folder = os.path.join(current_dir, 'static')

app = Flask(__name__, static_folder=static_folder)

def sanitize_filename_for_header(filename):
    """
    Sanitize filename for use in HTTP Content-Disposition header.
    Ensures the filename can be safely encoded in Latin-1 and doesn't break HTTP parsing.
    """
    if not filename:
        return "download"
    
    # Try to encode as Latin-1 first to catch any problematic characters
    try:
        # Test if it's already Latin-1 compatible
        filename.encode('latin-1')
        sanitized = filename
    except UnicodeEncodeError:
        # If not, we need to sanitize it
        # Normalize Unicode characters (decompose accented characters)
        normalized = unicodedata.normalize('NFKD', filename)
        sanitized = normalized
    
    # Remove control characters (0x00-0x1F, 0x7F-0x9F)
    sanitized = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', sanitized)
    
    # Replace characters that can't be encoded in Latin-1 (anything above 0xFF)
    try:
        sanitized.encode('latin-1')
    except UnicodeEncodeError:
        # Replace any character that can't be encoded in Latin-1 with underscore
        sanitized = ''.join(c if ord(c) <= 255 else '_' for c in sanitized)
    
    # Replace characters that are problematic in HTTP headers or filenames
    # Double quotes are especially problematic in Content-Disposition
    sanitized = re.sub(r'[<>:"|?*\\]', '_', sanitized)
    
    # Remove leading/trailing whitespace and dots (Windows compatibility)
    sanitized = sanitized.strip('. ')
    
    # Ensure the filename is not empty after sanitization
    if not sanitized:
        return "download"
    
    # Final safety check - ensure it can be encoded as Latin-1
    try:
        sanitized.encode('latin-1')
        return sanitized
    except UnicodeEncodeError:
        # Fallback: keep only ASCII printable characters
        return re.sub(r'[^\x20-\x7E]', '_', sanitized) or "download"


def get_config():
    """Get app configuration from config.json"""
    config_path = os.path.join(current_dir, 'config.json')
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        app.logger.error(f"Error loading config.json: {e}")
        return {}

# Function to check if a request is from an embedded context
def is_embedded_request():
    """
    Determine if the current request is from an embedded context.
    Returns True if the request origin is not in the allowed non-embedded origins.
    """
    config = get_config()
    non_embedded_origins = config.get('non_embedded_origins', [])

    # Check origin header
    origin, referer = print_origin()

    if origin and origin in non_embedded_origins:
        print('NOT EMBEDDED ACTUALLY')
        return False

    print('EMBEDDED ACTUALLY')

    # Check referer header as fallback
    if referer:
        for allowed_origin in non_embedded_origins:
            if referer.startswith(allowed_origin):
                return False



    # Default to False if neither header is present
    return False


def print_origin():
    origin = request.headers.get('Origin')
    referer = request.headers.get('Referer')
    # If not explicitly from a non-embedded origin, assume it's embedded
    # if origin or referer:
    #     embedded = True
    print("\n" + "*" * 50)
    print("*" + " " * 48 + "*")
    print("*" + " " * 15 + "EMBEDDED REQUEST" + " " * 15 + "*")
    print("*" + " " * 48 + "*")
    print("*" + " " * 10 + f"Origin: {origin or 'None'}" + " " * 10 + "*")
    print("*" + " " * 10 + f"Referer: {referer or 'None'}" + " " * 10 + "*")
    print("*" + " " * 48 + "*")
    print("*" * 50 + "\n")
    return origin, referer

# Enhanced CORS configuration - only for local development
# Lambda Function URL handles CORS in production
if os.environ.get('AWS_LAMBDA_FUNCTION_NAME') is None:
    print('cors!')
    # Running locally, enable Flask CORS
    cors = CORS(
        app,
        supports_credentials=True,
        resources={
            "/*": {
                "origins": "*",
                "allow_headers": ["Content-Type", "Authorization", "Accept"],
                "expose_headers": ["Content-Disposition"],
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
            }
        }
    )
    print("Local development: Flask CORS enabled")
else:
    print("Lambda environment: Using Lambda Function URL CORS")

db_config = db_utils.get_db_config()
app.config.update(db_config)

db.init_app(app)

migrate = Migrate(app, db)

USER = {
    "username": "jpnunez@3htp.com",
    "password": "user123"
}

USERS = [
    {
        "id": 1,
        "email": "usuario@ejemplo.com",
        "documentAccess": "Lectura",
        "chatAccess": True,
        "isAdmin": False
    },
    {
        "id": 2,
        "email": "admin@ejemplo.com",
        "documentAccess": "Lectura/Escritura",
        "chatAccess": True,
        "isAdmin": True
    },
    {
        "id": 3,
        "email": "invitado@ejemplo.com",
        "documentAccess": "Lectura",
        "chatAccess": False,
        "isAdmin": False
    }
]

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('username')
    password = data.get('password')

    # Import cognito authentication
    from cognito import authenticate_user

    # Try Cognito authentication first
    success, cognito_response = authenticate_user(email, password)
    print('\ncognito:', success, cognito_response)

    # Handle NEW_PASSWORD_REQUIRED challenge
    if not success and cognito_response.get("error") == "new_password_required":
        return jsonify({
            "success": False,
            "challenge": "new_password_required",
            "session": cognito_response.get("session"),
            "message": "New password required for first login",
            "error": "new_password_required"
        }), 200  # Use 200 status code for challenges, not errors

    if success:
        # Cognito authentication successful, check if user exists in local DB
        user = User.query.filter_by(email=email).first()

        if not user:
            return jsonify({
                "success": False,
                "message": "User authenticated but not found in system",
                "error": "user_not_in_system"
            }), 401

        # Check if this is an embedded request
        embedded = is_embedded_request()

        # Check if the user has chat access when in embedded mode
        if embedded and not user.chat_access:
            return jsonify({
                "success": False,
                "message": "You do not have access to chat functionality, which is required for embedded mode",
                "error": "no_chat_access"
            }), 403

        # Return JWT token for authentication
        return jsonify({
            "success": True,
            "role": user.role,
            "is_embedded": embedded,
            "token": cognito_response.get("idToken"),
            "cognito": cognito_response
        })
    else:
        # Cognito authentication failed
        error_message = cognito_response.get("error", "Credenciales inválidas")
        return jsonify({"success": False, "message": error_message}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    # JWT tokens are stateless, so logout is handled client-side
    # The frontend should delete the token from storage
    return jsonify({"success": True, "message": "Logged out successfully"})

@app.route('/api/refresh-token', methods=['POST'])
def refresh_token():
    """Refresh JWT tokens using refresh token"""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        refresh_token = data.get('refreshToken')
        if not refresh_token:
            return jsonify({"error": "Refresh token is required"}), 400
        
        # Import refresh token function
        from cognito import refresh_token as cognito_refresh_token
        
        # Refresh the tokens
        success, response_data = cognito_refresh_token(refresh_token)
        
        if success:
            return jsonify({
                "success": True,
                "token": response_data.get("idToken"),
                "accessToken": response_data.get("accessToken"),
                "expiresIn": response_data.get("expiresIn")
            })
        else:
            return jsonify({
                "success": False,
                "error": response_data.get("error", "Token refresh failed")
            }), 401
            
    except Exception as e:
        print(f"Refresh token endpoint error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/set-password', methods=['POST'])
def set_password():
    """Handle NEW_PASSWORD_REQUIRED challenge from Cognito"""
    print(f"[DEBUG] /api/set-password endpoint called")

    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    username = data.get('username')
    new_password = data.get('newPassword')
    session = data.get('session')

    print(f"[DEBUG] Set password request for user: {username}")

    if not username or not new_password or not session:
        return jsonify({"error": "Username, new password, and session are required"}), 400

    # Import cognito challenge response function
    from cognito import respond_to_auth_challenge

    # Respond to the challenge
    success, cognito_response = respond_to_auth_challenge(username, new_password, session)
    print(f"[DEBUG] Challenge response result: success={success}")

    if success:
        # Check if user exists in local DB
        user = User.query.filter_by(email=username).first()

        if not user:
            return jsonify({
                "success": False,
                "message": "User authenticated but not found in system",
                "error": "user_not_in_system"
            }), 401

        # Check if this is an embedded request
        embedded = is_embedded_request()

        # Check if the user has chat access when in embedded mode
        if embedded and not user.chat_access:
            return jsonify({
                "success": False,
                "message": "You do not have access to chat functionality, which is required for embedded mode",
                "error": "no_chat_access"
            }), 403

        # Return successful login response
        return jsonify({
            "success": True,
            "role": user.role,
            "is_embedded": embedded,
            "token": cognito_response.get("idToken"),
            "message": "Password updated and login successful",
            "cognito": cognito_response
        })
    else:
        # Password challenge failed
        error_message = cognito_response.get("error", "Failed to update password")
        return jsonify({"success": False, "message": error_message}), 400

@app.route('/api/forgot-password', methods=['POST'])
def forgot_password_endpoint():
    """Initiate forgot password flow"""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    username = data.get('username')
    if not username:
        return jsonify({"error": "Username/email is required"}), 400

    from cognito import forgot_password
    success, response = forgot_password(username)

    if success:
        return jsonify({
            "success": True,
            "message": response["message"],
            "destination": response.get("destination", "")
        }), 200
    else:
        return jsonify({
            "success": False,
            "error": response["error"]
        }), 400

@app.route('/api/confirm-forgot-password', methods=['POST'])
def confirm_forgot_password_endpoint():
    """Confirm forgot password with verification code"""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    username = data.get('username')
    verification_code = data.get('verificationCode')
    new_password = data.get('newPassword')

    if not username or not verification_code or not new_password:
        return jsonify({"error": "Username, verification code, and new password are required"}), 400

    from cognito import confirm_forgot_password
    success, response = confirm_forgot_password(username, verification_code, new_password)

    if success:
        return jsonify({
            "success": True,
            "message": response["message"]
        }), 200
    else:
        return jsonify({
            "success": False,
            "error": response["error"]
        }), 400

@app.route('/api/check-auth', methods=['GET'])
def check_auth():
    from auth_decorator import token_required
    from cognito import get_user_from_token
    from models import User

    success, user_data = get_user_from_token()

    if not success:
        return jsonify({"authenticated": False, "error": user_data.get("error")}), 401

    # Get user from database to ensure consistent role/permission data
    user_email = user_data.get("email")
    user = User.query.filter_by(email=user_email).first()

    # Use database as source of truth for roles and permissions
    if user:
        role = "admin" if user.is_admin else "user"
        is_admin = user.is_admin
        chat_access = user.chat_access
    else:
        # Fallback to token data if user not found in database
        role = user_data.get("role")
        is_admin = user_data.get("is_admin")
        chat_access = user_data.get("chat_access")

    embedded = is_embedded_request()
    return jsonify({
        "authenticated": True,
        "email": user_email,
        "role": role,
        "is_embedded": embedded,
        "is_admin": is_admin,
        "chat_access": chat_access
    })

@app.route('/api/embed/status', methods=['GET', 'OPTIONS'])
def embed_status():
    if request.method == 'OPTIONS':
        return '', 204
    return jsonify({
        "status": "ok",
        "version": "1.0.0",
        "embedEnabled": True,
        "features": [
            "authentication",
            "catalog_browsing",
            "document_viewing",
            "chat"
        ]
    })

@app.route('/api/check-chat-access', methods=['GET'])
@token_required
def check_chat_access(current_user=None, token_user_data=None, **kwargs):
    # Check if this is an embedded request
    embedded = is_embedded_request()

    return jsonify({
        "has_access": current_user.chat_access,
        "is_admin": current_user.is_admin,
        "user_email": current_user.email,
        "is_embedded": embedded
    })

@app.route('/api/allowed-domains', methods=['PUT'])
@admin_required
def allowed_domains(current_user=None, token_user_data=None, **kwargs):

    data = request.json
    print('allowed_domains', data)
    if not data or not data.get('domains'):
        return jsonify({"error": "El campo 'domains' es requerido"}), 400

    try:
        new_domains = data['domains']
        existing_domains = Domain.query.all()
        existing_domain_map = {d.id: d for d in existing_domains}

        for domain_data in new_domains:
            print('new domain', domain_data)
            if 'id' in domain_data and domain_data['id'] in existing_domain_map:
                print('if')
                domain = existing_domain_map[domain_data['id']]
                domain.name = domain_data['name']
            else:
                print('else', domain_data['name'])
                new_domain = Domain(name=domain_data['name'])
                print('new domain', new_domain)
                db.session.add(new_domain)

        db.session.commit()
        return jsonify({"success": True, "message": "Dominios actualizados correctamente"})
    except Exception as e:
        db.session.rollback()
        print(f"Error saving domains: {e}")
        return jsonify({"error": "Error al guardar dominios en la base de datos"}), 500

@app.route('/api/allowed-domains/<int:domain_id>', methods=['DELETE'])
@admin_required
def delete_domain(domain_id, current_user=None, token_user_data=None, **kwargs):

    try:
        domain = db.session.get(Domain, domain_id)
        if not domain:
            return jsonify({"error": "Dominio no encontrado"}), 404

        domain_name = domain.name
        if not domain_name.startswith('@'):
            domain_name = '@' + domain_name

        users_with_domain = User.query.filter(User.email.like(f'%{domain_name}')).all()

        if users_with_domain:
            return jsonify({
                "error": "domain_in_use_error",
                "users": [user.email for user in users_with_domain]
            }), 400

        db.session.delete(domain)
        db.session.commit()
        return jsonify({"success": True, "message": "Dominio eliminado correctamente"})
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting domain: {e}")
        return jsonify({"error": f"Error al eliminar dominio: {str(e)}"}), 500


@app.route('/api/i18n', methods=['GET'])
def get_translations():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, 'i18n/data.json')
    try:
        with open(json_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        app.logger.error(f"Data file not found: {json_path}")
        return {}
    except json.JSONDecodeError:
        app.logger.error(f"Invalid JSON in data file: {json_path}")
        return {
            "i18n_warning": "Error al obtener traducción",
        }
    return jsonify(TRANSLATIONS)

@app.route('/api/catalogs', methods=['GET'])
@token_required
def get_catalogs(current_user=None, token_user_data=None, **kwargs):
    for_chat = request.args.get('for_chat', 'false').lower() == 'true'
    catalogs = get_all_catalogs(user=current_user, for_chat=for_chat)
    return jsonify(catalogs)

@app.route('/api/catalogs', methods=['POST'])
@token_required
def create_catalog(current_user=None, token_user_data=None, **kwargs):
    data = request.json
    if not data or not data.get('catalog_name'):
        return jsonify({"error": "Catalog name is required"}), 400

    from catalog import create_catalog as create_new_catalog
    result = create_new_catalog(
        data.get('catalog_name'),
        data.get('description'),
        data.get('type')
    )

    if result:
        return jsonify({
            "success": True,
            "catalog": result
        })
    else:
        return jsonify({"error": "Failed to create catalog"}), 500

@app.route('/api/catalog-types', methods=['GET'])
@token_required
def get_types(current_user=None, token_user_data=None, **kwargs):
    from catalog import get_catalog_types
    catalog_types = get_catalog_types()
    return jsonify(catalog_types)

@app.route('/api/documents', methods=['GET'])
def get_documents():
    return get_catalogs()

@app.route('/api/catalogs/<int:catalog_id>', methods=['GET'])
@token_required
def get_catalog(catalog_id, current_user=None, token_user_data=None, **kwargs):
    print('catalog_id:', catalog_id)

    catalog = db.session.get(Catalog, catalog_id)
    if catalog:
        return jsonify(catalog.to_dict())

    return jsonify({"error": "Catálogo no encontrado"}), 404

@app.route('/api/documents/<path:doc_id>', methods=['GET'])
def get_document(doc_id):
    return get_catalog(doc_id)

@app.route('/api/catalogs/<string:catalog_id>/users', methods=['GET'])
@catalog_admin_required
def get_users_for_catalog(catalog_id, current_user=None, token_user_data=None, **kwargs):
    print('get_users_for_catalog:', catalog_id)

    from catalog import get_catalog_users
    users = get_catalog_users(catalog_id)
    return jsonify(users)

@app.route('/api/catalogs/<string:catalog_id>/available-users', methods=['GET'])
@catalog_admin_required
def get_available_users_for_catalog(catalog_id, current_user=None, token_user_data=None, **kwargs):
    from catalog import get_available_users_for_catalog as get_available_users
    available_users = get_available_users(catalog_id)
    return jsonify(available_users)

@app.route('/api/catalogs/<string:catalog_id>/users', methods=['POST'])
@catalog_admin_required
def add_user_to_catalog(catalog_id, current_user=None, token_user_data=None, **kwargs):
    data = request.json
    if not data or 'user_id' not in data or 'permission' not in data:
        return jsonify({"error": "Se requiere user_id y permission"}), 400

    user_id = data['user_id']
    permission_value = data['permission']

    from catalog import add_user_to_catalog as add_user
    result = add_user(catalog_id, user_id, permission_value)

    # Check if result is a tuple containing an error message and status code
    if isinstance(result, tuple) and len(result) == 2 and isinstance(result[0], dict) and 'error' in result[0]:
        return jsonify(result[0]), result[1]

    return jsonify(result)

@app.route('/api/catalogs/<string:catalog_id>/users/<int:user_id>', methods=['DELETE'])
@catalog_admin_required
def remove_user_from_catalog(catalog_id, user_id, current_user=None, token_user_data=None, **kwargs):
    from catalog import remove_user_from_catalog as remove_user
    result = remove_user(catalog_id, user_id)

    # Check if result is a tuple containing an error message and status code
    if isinstance(result, tuple) and len(result) == 2 and isinstance(result[0], dict) and 'error' in result[0]:
        return jsonify(result[0]), result[1]

    return jsonify(result)

@app.route('/api/catalogs/<string:catalog_id>/can-manage-permissions', methods=['GET'])
@token_required
def can_manage_catalog_permissions(catalog_id, current_user=None, token_user_data=None, **kwargs):
    """Check if current user can manage permissions for this catalog (admin or FULL permission)"""
    from models import CatalogPermission, PermissionType

    # Admin users can always manage permissions
    if current_user.is_admin:
        return jsonify({"can_manage": True, "reason": "admin"})

    # Check if user has FULL permission on this catalog
    catalog_permission = CatalogPermission.query.filter_by(
        catalog_id=catalog_id,
        user_id=current_user.id
    ).first()

    if catalog_permission and catalog_permission.permission == PermissionType.FULL:
        return jsonify({"can_manage": True, "reason": "full_permission"})

    return jsonify({"can_manage": False, "reason": "insufficient_permissions"})

@app.route('/api/catalogs/<string:catalog_id>/my-permission', methods=['GET'])
@token_required
def get_my_catalog_permission(catalog_id, current_user=None, token_user_data=None, **kwargs):
    """Get current user's permission for this catalog - for debugging purposes"""
    from models import CatalogPermission, PermissionType
    from sqlalchemy import text

    print(f"[DEBUG] get_my_catalog_permission called with:")
    print(f"[DEBUG]   catalog_id: {catalog_id} (type: {type(catalog_id)})")
    print(f"[DEBUG]   current_user.id: {current_user.id} (type: {type(current_user.id)})")
    print(f"[DEBUG]   current_user.email: {current_user.email}")
    print(f"[DEBUG] LOOKING FOR: catalog_id={catalog_id} AND user_id={current_user.id}")

    # Show the actual SQL query that will be executed
    query = CatalogPermission.query.filter_by(
        catalog_id=catalog_id,
        user_id=current_user.id
    )
    print(f"[DEBUG] SQL Query: {query}")

    catalog_permission = query.first()

    # Also check if there are any rows for this catalog at all
    all_permissions_for_catalog = CatalogPermission.query.filter_by(catalog_id=catalog_id).all()
    print(f"[DEBUG] Total permissions found for catalog {catalog_id}: {len(all_permissions_for_catalog)}")
    for perm in all_permissions_for_catalog:
        print(f"[DEBUG]   - User ID: {perm.user_id} (type: {type(perm.user_id)}), Permission: {perm.permission.value}")
        print(f"[DEBUG]   - COMPARISON: perm.user_id == current_user.id? {perm.user_id} == {current_user.id} = {perm.user_id == current_user.id}")

    # Check if there are any rows for this user at all
    all_permissions_for_user = CatalogPermission.query.filter_by(user_id=current_user.id).all()
    print(f"[DEBUG] Total permissions found for user {current_user.id}: {len(all_permissions_for_user)}")
    for perm in all_permissions_for_user:
        print(f"[DEBUG]   - Catalog ID: {perm.catalog_id} (type: {type(perm.catalog_id)}), Permission: {perm.permission.value}")
        print(f"[DEBUG]   - COMPARISON: perm.catalog_id == catalog_id? {perm.catalog_id} == {catalog_id} = {perm.catalog_id == catalog_id}")

    # Let's also try a manual direct query to see what's happening
    from sqlalchemy import and_
    manual_query = CatalogPermission.query.filter(
        and_(
            CatalogPermission.catalog_id == catalog_id,
            CatalogPermission.user_id == current_user.id
        )
    ).first()
    print(f"[DEBUG] Manual query result: {manual_query}")

    # And try with explicit type conversion
    try:
        catalog_id_int = int(catalog_id)
        int_query = CatalogPermission.query.filter_by(
            catalog_id=catalog_id_int,
            user_id=current_user.id
        ).first()
        print(f"[DEBUG] Query with int catalog_id ({catalog_id_int}): {int_query}")
    except ValueError:
        print(f"[DEBUG] Could not convert catalog_id '{catalog_id}' to int")

    if catalog_permission:
        print(f"[DEBUG] Query result: Found CatalogPermission")
        print(f"[DEBUG]   - catalog_id: {catalog_permission.catalog_id}")
        print(f"[DEBUG]   - user_id: {catalog_permission.user_id}")
        print(f"[DEBUG]   - permission: {catalog_permission.permission.value}")
        return jsonify({
            "has_permission_row": True,
            "permission": catalog_permission.permission.value,
            "catalog_id": catalog_permission.catalog_id,
            "user_id": catalog_permission.user_id,
            "user_email": current_user.email,
            "user_is_admin": current_user.is_admin
        })
    else:
        print(f"[DEBUG] Query result: None (no permission found)")
        print(f"[DEBUG] No permission found for catalog_id={catalog_id}, user_id={current_user.id}")
        return jsonify({
            "has_permission_row": False,
            "permission": None,
            "catalog_id": catalog_id,
            "user_id": current_user.id,
            "user_email": current_user.email,
            "user_is_admin": current_user.is_admin,
            "message": "NO ROW"
        })

@app.route('/api/catalogs/<string:catalog_id>/files', methods=['GET'])
@token_required
def get_files_for_catalog(catalog_id, current_user=None, token_user_data=None, **kwargs):
    from catalog import get_catalog_files
    files = get_catalog_files(catalog_id)
    return jsonify(files)


@app.route('/api/catalogs/<string:catalog_id>/upload', methods=['POST'])
@token_required
def upload_file_to_catalog(catalog_id, current_user=None, token_user_data=None, **kwargs):
    print(f"[DEBUG] Starting upload to catalog {catalog_id}")

    print(f"[DEBUG] User authenticated: {current_user.id}")
    print(f"[DEBUG] Request files: {request.files}")
    print(f"[DEBUG] Request form data: {request.form}")

    if 'file' not in request.files:
        print(f"[DEBUG] Error: No 'file' in request.files")
        return jsonify({"error": "No file provided"}), 400

    files = request.files.getlist('file')
    print(f"[DEBUG] Files list length: {len(files)}")

    if not files:
        print(f"[DEBUG] Error: Empty files list")
        return jsonify({"error": "No files provided"}), 400

    uploaded_files = []
    errors = []

    for index, file_obj in enumerate(files):
        print(f"[DEBUG] Processing file {index + 1}/{len(files)}: {file_obj.filename}")

        if file_obj.filename == '':
            print(f"[DEBUG] Skipping empty filename")
            continue

        try:
            print(f"[DEBUG] Reading file content for {file_obj.filename}")
            file_content = file_obj.read()
            content_type = file_obj.content_type
            print(f"[DEBUG] Content type: {content_type}, Content length: {len(file_content)} bytes")

            file_obj.seek(0)
            print(f"[DEBUG] Reset file pointer to beginning")

            print(f"[DEBUG] Calling catalog.upload_file_to_catalog for {file_obj.filename}")
            from catalog import upload_file_to_catalog as upload_catalog_file
            result = upload_catalog_file(catalog_id, file_obj, file_content, content_type)
            print(f"[DEBUG] Upload result: {result}")

            if result:
                uploaded_files.append(result)
                print(f"[DEBUG] Successfully uploaded {file_obj.filename}")
            else:
                errors.append(f"Failed to upload {file_obj.filename}")
                print(f"[DEBUG] Failed to upload {file_obj.filename} - no result returned")

        except Exception as e:
            print(f"[DEBUG] Exception during upload of {file_obj.filename}: {str(e)}")
            print(f"[DEBUG] Exception type: {type(e).__name__}")
            import traceback
            print(f"[DEBUG] Traceback: {traceback.format_exc()}")
            errors.append(f"Error uploading {file_obj.filename}: {str(e)}")

    print(f"[DEBUG] Upload process complete")
    print(f"[DEBUG] Successful uploads: {len(uploaded_files)}")
    print(f"[DEBUG] Failed uploads: {len(errors)}")

    if uploaded_files:
        print(f"[DEBUG] Returning success response")
        return jsonify({
            "success": True,
            "files": uploaded_files,
            "errors": errors if errors else None
        })
    else:
        print(f"[DEBUG] Returning failure response")
        return jsonify({
            "success": False,
            "error": "No files were uploaded successfully",
            "errors": errors
        }), 500

@app.route('/api/files/<int:file_id>/version', methods=['POST'])
@token_required
def upload_new_version(file_id, current_user=None, token_user_data=None, **kwargs):
    print("Starting upload_new_version function")

    try:
        print(f"Fetching file with id {file_id}")
        file = db.session.get(File, file_id)
        if not file:
            print("File not found")
            return jsonify({"error": "File not found"}), 404

        print(f"Fetching active version for file id {file_id}")
        active_version = Version.query.filter_by(file_id=file_id, active=True).first()
        if not active_version:
            print("No active version found for the file")
            return jsonify({"error": "No active version found for this file"}), 404

        if 'file' not in request.files:
            print("No file provided in the request")
            return jsonify({"error": "No file provided"}), 400

        file_obj = request.files['file']
        if file_obj.filename == '':
            print("No file selected")
            return jsonify({"error": "No selected file"}), 400

        file_content = file_obj.read()
        content_type = file_obj.content_type
        file_obj.seek(0)
        print(f"Uploaded file: {file_obj.filename}, size: {len(file_content)} bytes, content type: {content_type}")

        from aws_utils import get_client_with_assumed_role, upload_file_to_s3
        from db import get_bucket_name

        print("Fetching bucket name")
        bucket_name = get_bucket_name()
        if not bucket_name:
            print("S3 bucket configuration not found")
            return jsonify({"error": "S3 bucket configuration not found"}), 500

        catalog = db.session.get(Catalog, file.catalog_id)
        if not catalog:
            return jsonify({"error": "Catalog not found"}), 404

        s3_client = get_client_with_assumed_role('s3')
        # Use the sanitized s3Id from the catalog
        s3_folder_name = catalog.s3Id  # This is already sanitized
        versions_folder = f"catalog_dir/{s3_folder_name}/versions/"

        # Create versions folder if it doesn't exist
        try:
            print(f"Ensuring versions folder exists in S3: {versions_folder}")
            s3_client.put_object(
                Bucket=bucket_name,
                Key=versions_folder,
                Body=''
            )
        except Exception as e:
            traceback.print_exc()
            print(f"Could not create versions folder: {e}")

        # Move the active version to the versions folder
        old_s3_key = active_version.s3Id
        old_file_name = old_s3_key.split('/')[-1]
        new_versions_key = f"{versions_folder}{old_file_name}"

        try:
            print(f"Copying active version from {old_s3_key} to {new_versions_key}")
            s3_client.copy_object(
                Bucket=bucket_name,
                CopySource={'Bucket': bucket_name, 'Key': old_s3_key},
                Key=new_versions_key
            )

            print(f"Deleting old active version {old_s3_key} in S3")
            s3_client.delete_object(
                Bucket=bucket_name,
                Key=old_s3_key
            )

            active_version.s3Id = new_versions_key
            active_version.active = False
            print("Saving old active version in database")
            db.session.flush()
        except Exception as e:
            print(f"Error moving old version to versions folder: {e}")
            return jsonify({"error": f"Error moving old version to versions folder: {str(e)}"}), 500

        print(f"Using current user: {current_user.email}")
        user_id = current_user.id

        file_extension = ""
        if '.' in file_obj.filename:
            file_extension = file_obj.filename.rsplit('.', 1)[1].lower()

        new_version_number = active_version.version + 1
        print(f"Creating new version with version number: {new_version_number}")

        from io import BytesIO
        class FileWithCustomName:
            def __init__(self, content, filename):
                self.content = content
                self.filename = filename

            def read(self):
                return self.content

        new_version = Version(
            active=True,
            version=new_version_number,
            s3Id='',
            size=len(file_content),
            filename=file_obj.filename,
            uploader_id=user_id,
            file_id=file.id
        )

        print("Adding new version to database session")
        db.session.add(new_version)
        db.session.flush()

        new_filename = f"{catalog.id}-{file.id}-{new_version.id}"
        if file_extension:
            new_filename = f"{new_filename}.{file_extension}"
        print(f"New filename for S3: {new_filename}")

        custom_file_obj = FileWithCustomName(file_content, new_filename)

        print("Uploading new version to S3")
        s3_key = upload_file_to_s3(bucket_name, s3_folder_name, custom_file_obj, file_content, content_type)

        if not s3_key:
            print("Failed to upload new version to S3")
            db.session.rollback()
            return jsonify({"error": "Failed to upload new version to S3"}), 500

        new_version.s3Id = s3_key
        print(f"Uploaded new version with S3 key: {s3_key}")

        file.uploaded_at = datetime.now()
        file.size = len(file_content)

        print("Committing new version to database")
        db.session.commit()

        print("Successfully uploaded new version")
        return jsonify({
            "success": True,
            "file": file.to_dict(),
            "version": new_version.to_dict()
        })

    except Exception as e:
        print(f"Error during upload_new_version: {e}")
        traceback.print_exc()
        db.session.rollback()
        return jsonify({"error": f"Error uploading new version: {str(e)}"}), 500


@app.route('/api/files/<int:file_id>', methods=['PUT'])
@token_required
def update_file(file_id, current_user=None, token_user_data=None, **kwargs):

    try:
        file = db.session.get(File, file_id)
        if not file:
            return jsonify({"error": "File not found"}), 404

        data = request.json
        if not data:
            return jsonify({"error": "No se proporcionaron datos"}), 400

        if 'description' in data:
            file.summary = data['description']

        if 'status' in data:
            file.status = data['status']

        if 'confidentiality' in data:
            file.confidentiality = bool(data['confidentiality'])

        db.session.commit()

        return jsonify({
            "success": True,
            "file": file.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        print(f"Error updating file: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Error updating file: {str(e)}"}), 500

@app.route('/api/files/<int:file_id>/download', methods=['GET'])
@token_required
def download_file(file_id, current_user=None, token_user_data=None, **kwargs):

    try:
        file = db.session.get(File, file_id)
        if not file:
            return jsonify({"error": "File not found"}), 404

        active_version = Version.query.filter_by(file_id=file_id, active=True).first()
        if not active_version:
            return jsonify({"error": "No active version found for this file"}), 404

        from aws_utils import get_client_with_assumed_role
        from db import get_bucket_name
        import io

        bucket_name = get_bucket_name()
        if not bucket_name:
            return jsonify({"error": "S3 bucket configuration not found"}), 500

        s3_key = active_version.s3Id
        filename = active_version.filename
        s3_client = get_client_with_assumed_role('s3')

        try:
            s3_response = s3_client.get_object(
                Bucket=bucket_name,
                Key=s3_key
            )

            file_content = s3_response['Body'].read()

            # Use BytesIO and send_file for proper binary handling with Mangum
            from io import BytesIO
            file_io = BytesIO(file_content)
            file_io.seek(0)

            from flask import send_file
            response = send_file(
                file_io,
                mimetype=s3_response.get('ContentType', 'application/octet-stream'),
                as_attachment=True,
                download_name=filename
            )

            # Sanitize filename for Content-Disposition header
            sanitized_filename = sanitize_filename_for_header(filename)
            content_disposition = f'attachment; filename="{sanitized_filename}"'
            response.headers['Content-Disposition'] = content_disposition

            print(f"[DOWNLOAD DEBUG] Original filename: {filename}")
            print(f"[DOWNLOAD DEBUG] Sanitized filename: {sanitized_filename}")
            print(f"[DOWNLOAD DEBUG] Content-Disposition set to: {content_disposition}")
            print(f"[DOWNLOAD DEBUG] Response headers: {dict(response.headers)}")

            return response
        except Exception as e:
            traceback.print_exc()
            return jsonify({"error": f"Error retrieving file from S3: {str(e)}"}), 500

    except Exception as e:
        print(f"gral exception: {e}")
        traceback.print_exc()
        print(f"gral exception: post trace")
        return jsonify({"error": f"Error downloading file: {str(e)}"}), 500

@app.route('/api/download/<int:version_id>', methods=['GET'])
@token_required
def download_version(version_id, current_user=None, token_user_data=None, **kwargs):
    try:
        version = db.session.get(Version, version_id)
        if not version:
            return jsonify({"error": "Version not found"}), 404

        from aws_utils import get_client_with_assumed_role
        from db import get_bucket_name
        import io

        bucket_name = get_bucket_name()
        if not bucket_name:
            return jsonify({"error": "S3 bucket configuration not found"}), 500

        s3_client = get_client_with_assumed_role('s3')
        if not s3_client:
            return jsonify({"error": "S3 client not available"}), 500

        s3_object = s3_client.get_object(Bucket=bucket_name, Key=version.s3Id)
        file_content = s3_object['Body'].read()

        filename = version.filename or f"file_{version.id}"
        
        response = send_file(
            io.BytesIO(file_content),
            as_attachment=True,
            download_name=filename
        )

        return response

    except Exception as e:
        print(f"Error downloading version {version_id}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error downloading version: {str(e)}"}), 500

@app.route('/api/conversations/<int:catalog_id>', methods=['GET'])
@token_required
def get_conversation_messages(catalog_id, current_user=None, token_user_data=None, **kwargs):
    user_id = current_user.id

    try:
        from models import Conversation, Message

        # Find the conversation for this user and catalog
        conversation = Conversation.query.filter_by(
            speaker_id=user_id,
            catalog_id=catalog_id
        ).first()

        if not conversation:
            return jsonify([])  # Return empty array if no conversation exists

        # Get all messages for this conversation, ordered by creation time
        messages = Message.query.filter_by(
            conversation_id=conversation.id
        ).order_by(Message.created_at).all()

        # Convert messages to the format expected by the frontend
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                'id': msg.id,
                'type': 'user' if msg.is_request else 'system',
                'content': msg.message,
                'timestamp': msg.created_at.isoformat() if msg.created_at else None
            })

        return jsonify(formatted_messages)

    except Exception as e:
        print(f"Error fetching conversation messages: {e}")
        return jsonify({"error": "Error al cargar mensajes"}), 500


@app.route('/api/conversations/<int:catalog_id>/download-pdf', methods=['POST'])
@token_required
def download_conversation_pdf(catalog_id, current_user=None, token_user_data=None, **kwargs):
    user_id = current_user.id

    try:
        data = request.json
        message_count = data.get('message_count', 20)
        
        # Validate message count
        if not isinstance(message_count, int) or message_count <= 0:
            return jsonify({"error": "Invalid message count"}), 400

        from models import Conversation, Message, Catalog
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.units import inch
        from io import BytesIO
        import textwrap

        # Find the conversation for this user and catalog
        conversation = Conversation.query.filter_by(
            speaker_id=user_id,
            catalog_id=catalog_id
        ).first()

        if not conversation:
            return jsonify({"error": "No conversation found"}), 404

        # Get catalog info
        catalog = db.session.get(Catalog, catalog_id)
        if not catalog:
            return jsonify({"error": "Catalog not found"}), 404

        # Get the last N messages for this conversation, ordered by creation time
        messages = Message.query.filter_by(
            conversation_id=conversation.id
        ).order_by(Message.created_at.desc()).limit(message_count).all()
        
        # Reverse to get chronological order
        messages = list(reversed(messages))

        if not messages:
            return jsonify({"error": "No messages found in conversation"}), 404

        # Create PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                              rightMargin=72, leftMargin=72, 
                              topMargin=72, bottomMargin=18)
        
        # Container for the 'Flowable' objects
        story = []
        
        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        
        user_style = ParagraphStyle(
            'UserMessage',
            parent=styles['Normal'],
            fontSize=10,
            leftIndent=20,
            rightIndent=20,
            spaceAfter=12,
            backColor='#E3F2FD'
        )
        
        system_style = ParagraphStyle(
            'SystemMessage',
            parent=styles['Normal'],
            fontSize=10,
            leftIndent=20,
            rightIndent=20,
            spaceAfter=12,
            backColor='#F5F5F5'
        )
        
        header_style = ParagraphStyle(
            'MessageHeader',
            parent=styles['Normal'],
            fontSize=8,
            textColor='#666666',
            spaceAfter=6,
            leftIndent=20
        )

        # Add title
        title_text = f"Conversation: {catalog.name}"
        story.append(Paragraph(title_text, title_style))
        
        # Add metadata
        metadata_text = f"User: {current_user.email}<br/>Downloaded: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>Messages: {len(messages)}"
        story.append(Paragraph(metadata_text, styles['Normal']))
        story.append(Spacer(1, 20))

        # Add messages
        for msg in messages:
            # Message header with timestamp
            timestamp = msg.created_at.strftime('%Y-%m-%d %H:%M:%S') if msg.created_at else 'Unknown time'
            message_type = "You" if msg.is_request else "AI Assistant"
            header_text = f"{message_type} - {timestamp}"
            story.append(Paragraph(header_text, header_style))
            
            # Message content
            content = msg.message.replace('\n', '<br/>')
            # Escape HTML characters
            content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            content = content.replace('&lt;br/&gt;', '<br/>')
            
            message_style = user_style if msg.is_request else system_style
            story.append(Paragraph(content, message_style))
            story.append(Spacer(1, 10))

        # Build PDF
        doc.build(story)
        
        # Get PDF data
        pdf_data = buffer.getvalue()
        buffer.close()

        # Create filename
        safe_catalog_name = sanitize_filename_for_header(catalog.name)
        filename = f"conversation_{safe_catalog_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        # Return PDF as downloadable file
        from flask import send_file
        pdf_io = BytesIO(pdf_data)
        pdf_io.seek(0)

        response = send_file(
            pdf_io,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )

        # Set Content-Disposition header with sanitized filename
        sanitized_filename = sanitize_filename_for_header(filename)
        content_disposition = f'attachment; filename="{sanitized_filename}"'
        response.headers['Content-Disposition'] = content_disposition

        return response

    except Exception as e:
        print(f"Error generating conversation PDF: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Error generating PDF: {str(e)}"}), 500


@app.route('/api/chat', methods=['POST'])
@chat_access_required
def chat(current_user=None, token_user_data=None, **kwargs):
    data = request.json
    user_message = data.get('message', '')
    catalog = data.get('catalogId', '')

    if not user_message:
        return jsonify({"error": "El mensaje no puede estar vacío"}), 400

    user_id = current_user.id
    ai_response, message_id = generate_ai_response(user_message, catalog, user_id)
    create_activity_chat_log(EventType.CHAT_INTERACTION, current_user.email, catalog, message_id, 'spoke to the ai')

    return jsonify({
        "response": ai_response,
        "timestamp": None
    })

@app.route('/api/users', methods=['GET'])
@admin_required
def get_users(current_user=None, token_user_data=None, **kwargs):
    from users import get_users as get_all_users
    return get_all_users(current_user=current_user)

@app.route('/api/users/<int:user_id>', methods=['GET'])
@admin_required
def get_user(user_id, current_user=None, token_user_data=None, **kwargs):
    from users import get_user as get_single_user
    return get_single_user(user_id, current_user=current_user)

@app.route('/api/users', methods=['POST'])
@admin_required
def create_user(current_user=None, token_user_data=None, **kwargs):
    print(f"[DEBUG] /api/users POST endpoint called")
    print(f"[DEBUG] Request data: {request.json}")
    print(f"[DEBUG] Current user: {current_user.email if current_user else 'None'}")

    from users import create_user as create_new_user
    result = create_new_user(request.json, current_user=current_user)
    print(f"[DEBUG] create_new_user result type: {type(result)}")
    return result

@app.route('/api/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id, current_user=None, token_user_data=None, **kwargs):
    from users import update_user as update_existing_user
    return update_existing_user(user_id, request.json, current_user=current_user)

@app.route('/api/users/<int:user_id>/toggle/<string:property>', methods=['PUT'])
@admin_required
def toggle_user_property(user_id, property, current_user=None, token_user_data=None, **kwargs):
    from users import toggle_user_property as toggle_property
    return toggle_property(user_id, property, current_user=current_user)

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id, current_user=None, token_user_data=None, **kwargs):
    from users import delete_user as delete_existing_user
    return delete_existing_user(user_id, current_user=current_user)

@app.route('/api/logo/upload', methods=['POST'])
@admin_required
def upload_logo(current_user=None, token_user_data=None, **kwargs):
    """Upload and resize company logo"""
    try:
        if 'logo' not in request.files:
            return jsonify({"error": "No logo file provided"}), 400

        logo_file = request.files['logo']
        if logo_file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        # Read file content
        file_content = logo_file.read()

        # Validate it's an image
        try:
            from PIL import Image
            import io

            # Open and validate image
            image = Image.open(io.BytesIO(file_content))

            # Convert to RGB if necessary (handles RGBA, P mode, etc.)
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Resize image maintaining aspect ratio, max 128px on larger side
            width, height = image.size
            max_size = 128

            if width > height:
                new_width = max_size
                new_height = int((height * max_size) / width)
            else:
                new_height = max_size
                new_width = int((width * max_size) / height)

            # Resize image
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Convert back to bytes
            output_buffer = io.BytesIO()
            image.save(output_buffer, format='PNG', optimize=True)
            resized_content = output_buffer.getvalue()

        except Exception as e:
            return jsonify({"error": f"Invalid image file: {str(e)}"}), 400

        # Upload to S3 root
        from aws_utils import get_client_with_assumed_role
        from db import get_bucket_name

        bucket_name = get_bucket_name()
        if not bucket_name:
            return jsonify({"error": "S3 bucket configuration not found"}), 500

        s3_client = get_client_with_assumed_role('s3')

        try:
            # Upload logo to root of bucket as logo.png
            s3_client.put_object(
                Bucket=bucket_name,
                Key='logo.png',
                Body=resized_content,
                ContentType='image/png'
            )

            return jsonify({
                "success": True,
                "message": "Logo uploaded successfully",
                "size": f"{new_width}x{new_height}"
            })

        except Exception as e:
            return jsonify({"error": f"Failed to upload logo to S3: {str(e)}"}), 500

    except Exception as e:
        print(f"Error uploading logo: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Error uploading logo: {str(e)}"}), 500

@app.route('/api/logo', methods=['GET'])
def get_logo():
    """Retrieve company logo"""
    try:
        print(f"[LOGO DEBUG] v1 Starting logo retrieval")
        from aws_utils import get_client_with_assumed_role
        from db import get_bucket_name

        bucket_name = get_bucket_name()
        print(f"[LOGO DEBUG] Got bucket name: {bucket_name}")
        if not bucket_name:
            return jsonify({"error": "S3 bucket configuration not found", "location": "get_logo:bucket_check"}), 500

        # Try to get logo from S3 with retry logic
        for attempt in range(2):  # Try twice: initial attempt + 1 retry
            try:
                print(f"[LOGO DEBUG] Attempt {attempt + 1}: Getting S3 client")
                s3_client = get_client_with_assumed_role('s3')

                print(f"[LOGO DEBUG] Attempt {attempt + 1}: Calling S3 get_object")
                response = s3_client.get_object(
                    Bucket=bucket_name,
                    Key='logo.png'
                )

                print(f"[LOGO DEBUG] Attempt {attempt + 1}: Reading S3 response body")
                logo_content = response['Body'].read()
                print(f"[LOGO DEBUG] Attempt {attempt + 1}: Read {len(logo_content)} bytes")

                print(f"[LOGO DEBUG] Attempt {attempt + 1}: Creating BytesIO object for send_file")
                from io import BytesIO
                logo_io = BytesIO(logo_content)
                logo_io.seek(0)

                print(f"[LOGO DEBUG] Attempt {attempt + 1}: Using send_file for binary response")
                from flask import send_file

                response_obj = send_file(
                    logo_io,
                    mimetype='image/png',
                    as_attachment=False,
                    download_name='logo.png'
                )

                print(f"[LOGO DEBUG] Attempt {attempt + 1}: Setting cache headers on send_file response")
                # Force no caching - set headers explicitly after response creation
                response_obj.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response_obj.headers['Pragma'] = 'no-cache'
                response_obj.headers['Expires'] = '0'

                print(f"[LOGO DEBUG] Attempt {attempt + 1}: Returning send_file response object")
                return response_obj

            except ClientError as e:
                print(f"[LOGO DEBUG] client error except Attempt {attempt + 1}: ClientError occurred")
                error_code = e.response.get('Error', {}).get('Code')
                if error_code == 'NoSuchKey':
                    # Logo doesn't exist, return 404
                    print(f"[LOGO DEBUG] Logo not found in S3")
                    return jsonify({"error": "Logo not found", "location": f"get_logo:s3_not_found:attempt_{attempt+1}"}), 404
                elif error_code in ['InvalidAccessKeyId', 'SignatureDoesNotMatch', 'TokenRefreshRequired', 'ExpiredToken'] and attempt == 0:
                    # Credential-related error on first attempt, force refresh and retry
                    print(f"[LOGO DEBUG] Credential error on logo retrieval: {error_code}, forcing credential refresh")
                    import aws_utils
                    aws_utils._credentials = None  # Force refresh
                    aws_utils._credentials_expiry = 0
                    if not aws_utils.refresh_credentials():
                        return jsonify({"error": "Failed to refresh AWS credentials", "location": f"get_logo:credential_refresh_failed:attempt_{attempt+1}"}), 500
                    continue  # Retry with new credentials
                else:
                    print(f"[LOGO DEBUG] Other ClientError: {str(e)}")
                    return jsonify({"error": f"Error retrieving logo: {str(e)}", "location": f"get_logo:client_error:attempt_{attempt+1}", "error_code": error_code}), 500
            except Exception as e:
                print(f"[LOGO DEBUG] gral except! Attempt {attempt + 1}: General Exception: {str(e)}")
                print(f"[LOGO DEBUG] gral except! Exception type: {type(e).__name__}")
                import traceback
                traceback.print_exc()
                if attempt == 0:
                    print(f"[LOGO DEBUG] Retrying after unexpected error: {str(e)}")
                    continue
                else:
                    return jsonify({
                        "error": f"Error retrieving logo: {str(e)}",
                        "location": f"get_logo:general_exception:attempt_{attempt+1}",
                        "exception_type": type(e).__name__,
                        "traceback": traceback.format_exc()
                    }), 500

    except Exception as e:
        print(f"[LOGO DEBUG] Outer exception: {e}")
        print(f"[LOGO DEBUG] Outer exception type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": f"Error retrieving logo: {str(e)}",
            "location": "get_logo:outer_exception",
            "exception_type": type(e).__name__,
            "traceback": traceback.format_exc()
        }), 500

@app.route('/api/activity-logs', methods=['GET'])
@admin_required
def get_activity_logs(current_user=None, token_user_data=None, **kwargs):

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

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_static_files(path):
    static_mode = os.environ.get('STATIC_MODE', 'true').lower() == 'true'  # Default to true

    if not static_mode:
        return jsonify({"error": "No encontrado"}), 404

    print(f"Static mode request path: {path}")

    try:
        if not path:
            print("Serving index.html for root path")
            return send_from_directory(app.static_folder, 'index.html')

        if path.startswith('api/'):
            print(f"API request: {path}, letting Flask routes handle it")
            return jsonify({"error": "Endpoint de API no encontrado"}), 404

        file_path = os.path.join(app.static_folder, path)
        if os.path.isfile(file_path):
            print(f"Serving static file: {path}")
            return send_from_directory(app.static_folder, path)

        print(f"No static file found for {path}, serving index.html")
        return send_from_directory(app.static_folder, 'index.html')
    except Exception as e:
        print(f"Error serving file: {str(e)}")
        return f"Error: {str(e)}", 500

with app.app_context():
    try:
        if db_utils.test_connection(app):
            print("Database connection test successful")
        else:
            print("Database connection test failed")
    except Exception as e:
        print(f"Error testing database connection: {e}")

@app.cli.command("init-db")
def init_db_command():
    """Clear existing data and create new tables."""
    try:
        db.drop_all()
        db.create_all()
        print("Database initialized successfully")

        admin = User(
            email="admin@example.com",
            original_username="admin@example.com",
            document_access="Lectura/Escritura",
            chat_access=True,
            is_admin=True,
            role="admin"
        )

        user = User(
            email="user@example.com",
            original_username="user@example.com",
            document_access="Lectura",
            chat_access=True,
            is_admin=False,
            role="user"
        )

        db.session.add(admin)
        db.session.add(user)
        db.session.commit()

        db.session.commit()

        print("Default data seeded successfully")
        return True
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False

if __name__ == '__main__':
    static_mode = os.environ.get('STATIC_MODE', 'true').lower() == 'true'
    if static_mode:
        print(f"Ejecutando en MODO ESTÁTICO - sirviendo archivos estáticos desde {static_folder}")

    print(f"Servidor ejecutándose en http://0.0.0.0:8000")
    app.run(host='0.0.0.0', port=8000)
