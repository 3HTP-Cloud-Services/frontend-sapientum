from flask import Flask, request, jsonify, send_from_directory, send_file, Response
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
import json
from io import BytesIO
from models import db, User, Domain, Catalog, File, Version, ActivityLog, EventType, Parameter, Message, Conversation
import db as db_utils
import traceback
from datetime import datetime
from werkzeug.local import LocalProxy
from chat import generate_ai_response
from activity import create_activity_chat_log, get_activity_logs_with_pagination
from urllib.parse import quote
from auth_decorator import token_required, admin_required, chat_access_required, catalog_admin_required, invoker_required
from botocore.exceptions import ClientError
import re
import unicodedata
from pdf import generate_conversation_pdf
from logo import upload_logo, get_logo
from catalog_files import upload_new_version, download_file, update_file

from catalog import get_all_catalogs

current_dir = os.path.dirname(os.path.abspath(__file__))
static_folder = os.path.join(current_dir, 'static')

app = Flask(__name__, static_folder=static_folder)

app_parameters = {}

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
    import io
    import sys
    import traceback as tb

    log_capture = io.StringIO()
    original_stdout = sys.stdout
    original_stderr = sys.stderr

    class TeeStream:
        def __init__(self, original, capture):
            self.original = original
            self.capture = capture

        def write(self, data):
            self.original.write(data)
            self.capture.write(data)

        def flush(self):
            self.original.flush()
            self.capture.flush()

    sys.stdout = TeeStream(original_stdout, log_capture)
    sys.stderr = TeeStream(original_stderr, log_capture)

    try:
        print('[DEBUG] Login endpoint called')
        data = request.json
        email = data.get('username')
        password = data.get('password')
        print(f'[DEBUG] Login attempt for email: {email}')

        # Import cognito authentication
        from cognito import authenticate_user

        # Try Cognito authentication first
        print('[DEBUG] Calling authenticate_user')
        success, cognito_response = authenticate_user(email, password)
        print(f'\n[DEBUG] Cognito response - success: {success}, response: {cognito_response}')

        # Handle NEW_PASSWORD_REQUIRED challenge
        if not success and cognito_response.get("error") == "new_password_required":
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            return jsonify({
                "success": False,
                "challenge": "new_password_required",
                "session": cognito_response.get("session"),
                "message": "New password required for first login",
                "error": "new_password_required",
            }), 200

        if success:
            # Cognito authentication successful, check if user exists in local DB
            print('[DEBUG] Cognito authentication successful, checking local DB')
            user = User.query.filter_by(email=email).first()

            if not user:
                print(f'[DEBUG] User {email} not found in local DB')
                sys.stdout = original_stdout
                sys.stderr = original_stderr
                return jsonify({
                    "success": False,
                    "message": "User authenticated but not found in system",
                    "error": "user_not_in_system",
                }), 401

            print(f'[DEBUG] User found: {user.email}, role: {user.role}')

            # Check if this is an embedded request
            embedded = is_embedded_request()
            print(f'[DEBUG] Is embedded request: {embedded}')

            # Check if the user has chat access when in embedded mode
            if embedded and not user.chat_access:
                print(f'[DEBUG] User does not have chat access in embedded mode')
                sys.stdout = original_stdout
                sys.stderr = original_stderr
                return jsonify({
                    "success": False,
                    "message": "You do not have access to chat functionality, which is required for embedded mode",
                    "error": "no_chat_access",
                }), 403

            print('[DEBUG] Login successful, returning token')
            sys.stdout = original_stdout
            sys.stderr = original_stderr

            # Return JWT token for authentication
            return jsonify({
                "success": True,
                "role": user.role,
                "is_embedded": embedded,
                "token": cognito_response.get("idToken"),
                "cognito": cognito_response,
            })
        else:
            # Cognito authentication failed
            print(f'[DEBUG] Cognito authentication failed')
            error_message = cognito_response.get("error", "Credenciales inválidas")
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            return jsonify({
                "success": False,
                "message": error_message,
            }), 401

    except Exception as e:
        print(f'[ERROR] Login endpoint error: {e}')
        tb.print_exc()

        sys.stdout = original_stdout
        sys.stderr = original_stderr

        return jsonify({
            "success": False,
            "error": "Error interno del servidor"
        }), 500
    finally:
        sys.stdout = original_stdout
        sys.stderr = original_stderr

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
    print("[I18N DEBUG] Starting get_translations function")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, 'i18n/data.json')
    print(f"[I18N DEBUG] Current directory: {current_dir}")
    print(f"[I18N DEBUG] JSON path: {json_path}")
    print(f"[I18N DEBUG] File exists: {os.path.exists(json_path)}")

    try:
        print("[I18N DEBUG] Attempting to open i18n data file")
        with open(json_path, 'r', encoding='utf-8') as file:
            print("[I18N DEBUG] File opened successfully, reading JSON")
            data = json.load(file)
            print(f"[I18N DEBUG] JSON loaded successfully, keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            print(f"[I18N DEBUG] Data sample: {str(data)[:200]}...")
            return data
    except FileNotFoundError as e:
        print(f"[I18N DEBUG] FileNotFoundError: {e}")
        app.logger.error(f"Data file not found: {json_path}")
        return {}
    except json.JSONDecodeError as e:
        print(f"[I18N DEBUG] JSONDecodeError: {e}")
        app.logger.error(f"Invalid JSON in data file: {json_path}")
        return {
            "i18n_warning": "Error al obtener traducción",
        }
    except Exception as e:
        print(f"[I18N DEBUG] Unexpected error: {e}")
        print(f"[I18N DEBUG] Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return {
            "i18n_error": f"Unexpected error: {str(e)}",
        }

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

    # Validate catalog name format
    catalog_name = data.get('catalog_name')
    catalog_name_pattern = r'^[a-z0-9][a-z0-9_-]{0,99}$'
    if not re.match(catalog_name_pattern, catalog_name):
        return jsonify({
            "error": "Invalid catalog name. Must start with lowercase letter or digit, contain only lowercase letters, digits, underscores, and hyphens, and be 1-100 characters long."
        }), 400

    # Extract JWT token from request headers
    jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')

    # Call external catalog creation API
    from catalog import call_external_catalog_api
    api_success, api_response = call_external_catalog_api(
        catalog_name=data.get('catalog_name'),
        catalog_type=data.get('type', 'General'),
        description=data.get('description'),
        instruction=data.get('instruction'),
        apply=True,
        jwt_token=jwt_token
    )

    # Log the external API response
    print("=" * 80)
    print(f"EXTERNAL API CALL RESULT: {'SUCCESS' if api_success else 'FAILED'}")
    print("=" * 80)
    print("Full external API response object:")
    import json
    print(json.dumps(api_response, indent=2, ensure_ascii=False))
    print("=" * 80)

    # Continue with local catalog creation
    from catalog import create_catalog as create_new_catalog
    result = create_new_catalog(
        data.get('catalog_name'),
        data.get('description'),
        data.get('type')
    )

    if result:
        print("=" * 80)
        print("TRIGGERING STEP FUNCTION FOR CATALOG STATUS POLLING")
        print("=" * 80)
        print(f"Catalog Name: {data.get('catalog_name')}")
        print(f"Local Catalog ID: {result.get('id')}")
        print(f"JWT Token Present: {bool(jwt_token)}")
        print(f"JWT Token Length: {len(jwt_token) if jwt_token else 0}")

        # Trigger Step Function to poll catalog status
        from catalog import trigger_catalog_status_poller
        poller_success, execution_arn, error_details = trigger_catalog_status_poller(
            catalog_name=data.get('catalog_name'),
            local_catalog_id=result.get('id'),
            jwt_token=jwt_token
        )

        print(f"Step Function Trigger Result:")
        print(f"  - Success: {poller_success}")
        print(f"  - Execution ARN: {execution_arn}")
        if error_details:
            print(f"  - Error: {error_details}")
        print("=" * 80)

        step_function_response = {
            "triggered": poller_success,
            "execution_arn": execution_arn
        }

        if poller_success:
            step_function_response["message"] = "Step Function started - will poll catalog status every 20s for up to 50 minutes"
            step_function_response["polling_interval"] = "20 seconds"
            step_function_response["max_attempts"] = 150
        else:
            step_function_response["message"] = "Failed to trigger Step Function"
            step_function_response["error"] = error_details

        return jsonify({
            "success": True,
            "catalog": result,
            "external_api": {
                "success": api_success,
                "response": api_response
            },
            "step_function": step_function_response
        })
    else:
        return jsonify({
            "error": "Failed to create catalog locally",
            "external_api": {
                "success": api_success,
                "response": api_response
            }
        }), 500

@app.route('/api/catalog-types', methods=['GET'])
@token_required
def get_types(current_user=None, token_user_data=None, **kwargs):
    from catalog import get_catalog_types
    catalog_types = get_catalog_types()
    return jsonify(catalog_types)

@app.route('/api/catalogs/<int:catalog_id>/status', methods=['GET'])
@token_required
def get_catalog_status(catalog_id, current_user=None, token_user_data=None, **kwargs):
    """Get only the AWS resource IDs for a catalog"""
    try:
        catalog = Catalog.query.filter_by(id=catalog_id, is_active=True).first()
        if not catalog:
            return jsonify({"error": "Catalog not found"}), 404

        return jsonify({
            "knowledge_base_id": catalog.knowledge_base_id,
            "data_source_id": catalog.data_source_id,
            "agent_id": catalog.agent_id,
            "agent_version_id": catalog.agent_version_id
        })
    except Exception as e:
        print(f"Error getting catalog status: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/catalogs/status/batch', methods=['POST'])
@token_required
def get_catalogs_status_batch(current_user=None, token_user_data=None, **kwargs):
    """Get AWS resource IDs for multiple catalogs"""
    try:
        data = request.json
        if not data or 'ids' not in data:
            return jsonify({"error": "Catalog IDs are required"}), 400

        catalog_ids = data['ids']
        if not isinstance(catalog_ids, list):
            return jsonify({"error": "IDs must be a list"}), 400

        # Limit to 20 catalogs per request
        if len(catalog_ids) > 20:
            return jsonify({"error": "Maximum 20 catalog IDs per request"}), 400

        # Query all catalogs at once
        catalogs = Catalog.query.filter(Catalog.id.in_(catalog_ids), Catalog.is_active == True).all()

        # Build response dict keyed by catalog ID
        result = {}
        for catalog in catalogs:
            result[str(catalog.id)] = {
                "knowledge_base_id": catalog.knowledge_base_id,
                "data_source_id": catalog.data_source_id,
                "agent_id": catalog.agent_id,
                "agent_version_id": catalog.agent_version_id
            }

        return jsonify(result)
    except Exception as e:
        print(f"Error getting catalogs status batch: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

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

@app.route('/api/catalogs/<int:catalog_id>/update-aws-resources', methods=['POST'])
@token_required
def update_catalog_aws_resources(catalog_id, current_user=None, token_user_data=None, **kwargs):
    """
    Update catalog with AWS resource IDs from the Step Function
    This endpoint is called by the UpdateCatalogDB Lambda function
    Requires valid JWT token
    """
    print(f"[UPDATE_AWS_RESOURCES] ===== RECEIVED REQUEST =====")
    print(f"[UPDATE_AWS_RESOURCES] Catalog ID: {catalog_id}")
    print(f"[UPDATE_AWS_RESOURCES] Called by user: {current_user.email}")
    print(f"[UPDATE_AWS_RESOURCES] JWT token received and validated successfully")

    try:
        data = request.get_json()
        print(f"[UPDATE_AWS_RESOURCES] Request body:")
        print(json.dumps(data, indent=2))

        knowledge_base_id = data.get('knowledge_base_id')
        data_source_id = data.get('data_source_id')
        agent_id = data.get('agent_id')
        agent_alias_id = data.get('agent_alias_id')

        print(f"[UPDATE_AWS_RESOURCES] Extracted values:")
        print(f"  - knowledge_base_id: {knowledge_base_id}")
        print(f"  - data_source_id: {data_source_id}")
        print(f"  - agent_id: {agent_id}")
        print(f"  - agent_alias_id: {agent_alias_id}")

        if not knowledge_base_id or not data_source_id:
            error_msg = "Missing required fields: knowledge_base_id and data_source_id"
            print(f"[UPDATE_AWS_RESOURCES] ERROR: {error_msg}")
            return jsonify({"success": False, "error": error_msg}), 400

        # Find the catalog
        catalog = db.session.get(Catalog, catalog_id)
        if not catalog:
            error_msg = f"Catalog {catalog_id} not found"
            print(f"[UPDATE_AWS_RESOURCES] ERROR: {error_msg}")
            return jsonify({"success": False, "error": error_msg}), 404

        print(f"[UPDATE_AWS_RESOURCES] Found catalog: {catalog.name}")
        print(f"[UPDATE_AWS_RESOURCES] Current values:")
        print(f"  - knowledge_base_id: {catalog.knowledge_base_id}")
        print(f"  - data_source_id: {catalog.data_source_id}")
        print(f"  - agent_id: {catalog.agent_id}")
        print(f"  - agent_version_id: {catalog.agent_version_id}")

        # Update the catalog
        catalog.knowledge_base_id = knowledge_base_id
        catalog.data_source_id = data_source_id
        if agent_id:
            catalog.agent_id = agent_id
        if agent_alias_id:
            catalog.agent_version_id = agent_alias_id
        catalog.updated_at = datetime.utcnow()

        db.session.commit()

        print(f"[UPDATE_AWS_RESOURCES] ===== UPDATE SUCCESSFUL =====")
        print(f"[UPDATE_AWS_RESOURCES] Updated catalog {catalog_id}")
        print(f"[UPDATE_AWS_RESOURCES] New values:")
        print(f"  - knowledge_base_id: {catalog.knowledge_base_id}")
        print(f"  - data_source_id: {catalog.data_source_id}")
        print(f"  - agent_id: {catalog.agent_id}")
        print(f"  - agent_version_id: {catalog.agent_version_id}")

        result = {
            "success": True,
            "catalog_id": catalog_id,
            "catalog_name": catalog.name,
            "knowledge_base_id": knowledge_base_id,
            "data_source_id": data_source_id,
            "agent_id": agent_id,
            "agent_alias_id": agent_alias_id,
            "updated_at": catalog.updated_at.isoformat()
        }

        print(f"[UPDATE_AWS_RESOURCES] Returning result:")
        print(json.dumps(result, indent=2))

        return jsonify(result), 200

    except Exception as e:
        error_msg = f"Error updating catalog: {str(e)}"
        print(f"[UPDATE_AWS_RESOURCES] ERROR: {error_msg}")
        traceback.print_exc()
        return jsonify({"success": False, "error": error_msg}), 500

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


@app.route('/api/catalogs/<string:catalog_id>/generate-upload-url', methods=['POST'])
@token_required
def generate_upload_url(catalog_id, current_user=None, token_user_data=None, **kwargs):
    try:
        data = request.json
        filename = data.get('filename')
        content_type = data.get('content_type', 'application/octet-stream')

        if not filename:
            return jsonify({"error": "Filename is required"}), 400

        from catalog import generate_presigned_upload_url
        result = generate_presigned_upload_url(catalog_id, filename, content_type, current_user)

        if result:
            return jsonify(result)
        else:
            return jsonify({"error": "Failed to generate upload URL"}), 500

    except Exception as e:
        print(f"Error generating upload URL: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/catalogs/<string:catalog_id>/upload-complete', methods=['POST'])
@token_required
def upload_complete(catalog_id, current_user=None, token_user_data=None, **kwargs):
    try:
        data = request.json
        s3_key = data.get('s3_key')
        filename = data.get('filename')
        file_size = data.get('file_size')
        file_id = data.get('file_id')
        version_id = data.get('version_id')

        if not all([s3_key, filename, file_size, file_id, version_id]):
            return jsonify({"error": "Missing required fields"}), 400

        from catalog import finalize_file_upload
        result = finalize_file_upload(catalog_id, s3_key, filename, file_size, file_id, version_id, current_user)

        if result:
            return jsonify(result)
        else:
            return jsonify({"error": "Failed to finalize upload"}), 500

    except Exception as e:
        print(f"Error finalizing upload: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

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
def upload_new_version_endpoint(file_id, current_user=None, token_user_data=None, **kwargs):
    """Upload a new version of an existing file"""
    return upload_new_version(file_id, current_user.id, current_user.email)

@app.route('/api/files/<int:file_id>/generate-version-upload-url', methods=['POST'])
@token_required
def generate_version_upload_url(file_id, current_user=None, token_user_data=None, **kwargs):
    try:
        data = request.json
        filename = data.get('filename')
        content_type = data.get('content_type', 'application/octet-stream')

        if not filename:
            return jsonify({"error": "Filename is required"}), 400

        from catalog_files import generate_presigned_version_upload_url
        result = generate_presigned_version_upload_url(file_id, filename, content_type, current_user)

        if result:
            return jsonify(result)
        else:
            return jsonify({"error": "Failed to generate version upload URL"}), 500

    except Exception as e:
        print(f"Error generating version upload URL: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/files/<int:file_id>/version-upload-complete', methods=['POST'])
@token_required
def version_upload_complete(file_id, current_user=None, token_user_data=None, **kwargs):
    try:
        data = request.json
        s3_key = data.get('s3_key')
        filename = data.get('filename')
        file_size = data.get('file_size')
        version_id = data.get('version_id')

        if not all([s3_key, filename, file_size, version_id]):
            return jsonify({"error": "Missing required fields"}), 400

        from catalog_files import finalize_version_upload
        result = finalize_version_upload(file_id, s3_key, filename, file_size, version_id, current_user)

        if result:
            return jsonify(result)
        else:
            return jsonify({"error": "Failed to finalize version upload"}), 500

    except Exception as e:
        print(f"Error finalizing version upload: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/files/<int:file_id>', methods=['PUT'])
@token_required
def update_file_endpoint(file_id, current_user=None, token_user_data=None, **kwargs):
    """Update file metadata (description, status, confidentiality)"""
    return update_file(file_id)

@app.route('/api/files/<int:file_id>/download', methods=['GET'])
@token_required
def download_file_endpoint(file_id, current_user=None, token_user_data=None, **kwargs):
    """Download the active version of a file"""
    return download_file(file_id)

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
        from sqlalchemy import func

        conversation = Conversation.query.filter_by(
            speaker_id=user_id,
            catalog_id=catalog_id
        ).first()

        if not conversation:
            return jsonify([])

        user_message_limit = request.args.get('user_message_limit', type=int)
        before_message_id = request.args.get('before_message_id', type=int)

        if user_message_limit is not None and user_message_limit > 0:
            query = Message.query.filter_by(
                conversation_id=conversation.id,
                is_request=True
            )

            if before_message_id is not None:
                query = query.filter(Message.id < before_message_id)

            user_messages = query.order_by(Message.id.desc()).limit(user_message_limit).all()

            if not user_messages:
                return jsonify([])

            user_message_ids = [msg.id for msg in user_messages]
            oldest_user_message_id = min(user_message_ids)

            messages = Message.query.filter_by(
                conversation_id=conversation.id
            ).filter(Message.id >= oldest_user_message_id).order_by(Message.id.asc()).all()

            if before_message_id is not None:
                messages = [m for m in messages if m.id < before_message_id]
        else:
            messages = Message.query.filter_by(
                conversation_id=conversation.id
            ).order_by(Message.id.asc()).all()

        import json
        from crypto_utils import decrypt_triplet

        version_lookup = {}
        for msg in messages:
            if msg.citations and msg.citations.strip() and msg.encryption_key:
                try:
                    raw_citations = json.loads(msg.citations)
                    for citation in raw_citations:
                        encrypted_triplet = citation.get('encrypted_triplet')
                        if encrypted_triplet:
                            catalog_id, file_id, version_id = decrypt_triplet(encrypted_triplet, msg.encryption_key)
                            if catalog_id and file_id and version_id:
                                version_lookup[(catalog_id, file_id, version_id)] = None
                except json.JSONDecodeError:
                    continue

        if version_lookup:
            version_ids = [vid for (_, _, vid) in version_lookup.keys()]

            versions = Version.query.filter(Version.id.in_(version_ids)).all()

            for version_obj in versions:
                version_lookup[(version_obj.file.catalog_id, version_obj.file_id, version_obj.id)] = version_obj.filename

        formatted_messages = []
        for msg in messages:
            citations_data = []
            if msg.citations and msg.citations.strip():
                try:
                    raw_citations = json.loads(msg.citations)

                    for citation in raw_citations:
                        encrypted_triplet = citation.get('encrypted_triplet')

                        if encrypted_triplet and msg.encryption_key:
                            catalog_id, file_id, version_id = decrypt_triplet(encrypted_triplet, msg.encryption_key)
                            if catalog_id and file_id and version_id:
                                resolved_name = version_lookup.get((catalog_id, file_id, version_id), encrypted_triplet)
                                citation['resolved_filename'] = resolved_name
                            else:
                                citation['resolved_filename'] = encrypted_triplet
                        else:
                            citation['resolved_filename'] = citation.get('encrypted_triplet', 'Unknown')
                            citation.pop('encrypted_triplet', None)

                        citations_data.append(citation)
                except json.JSONDecodeError:
                    print(f"Warning: Failed to parse citations for message {msg.id}")
                    citations_data = []

            formatted_messages.append({
                'id': msg.id,
                'type': 'user' if msg.is_request else 'system',
                'content': msg.message,
                'timestamp': msg.created_at.isoformat() if msg.created_at else None,
                'has_trace': bool(msg.trace and msg.trace.strip()),
                'citations': citations_data
            })

        return jsonify(formatted_messages)

    except Exception as e:
        print(f"Error fetching conversation messages: {e}")
        return jsonify({"error": "Error al cargar mensajes"}), 500


@app.route('/api/messages/<int:message_id>/trace', methods=['GET'])
@token_required
def get_message_trace(message_id, current_user=None, token_user_data=None, **kwargs):
    try:
        from models import Message, Conversation

        # Get the message and verify user has access to it
        message = Message.query.join(Conversation).filter(
            Message.id == message_id,
            Conversation.speaker_id == current_user.id
        ).first()

        if not message:
            return jsonify({"error": "Message not found or access denied"}), 404

        # Return trace data if it exists
        if message.trace and message.trace.strip():
            try:
                import json
                trace_data = json.loads(message.trace)
                return jsonify({
                    "success": True,
                    "trace": trace_data
                })
            except json.JSONDecodeError:
                return jsonify({
                    "success": True,
                    "trace": message.trace
                })
        else:
            return jsonify({"error": "No trace data available for this message"}), 404

    except Exception as e:
        print(f"Error fetching message trace: {e}")
        return jsonify({"error": "Error fetching trace data"}), 500


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

        # Generate PDF using the pdf module
        pdf_data, filename = generate_conversation_pdf(catalog_id, user_id, message_count)

        if pdf_data is None:
            return jsonify({"error": filename}), 404

        # Return PDF as downloadable file
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
@token_required
def chat(current_user=None, token_user_data=None, **kwargs):
    import io
    import sys
    import traceback as tb

    log_capture = io.StringIO()
    original_stdout = sys.stdout
    original_stderr = sys.stderr

    class TeeStream:
        def __init__(self, original, capture):
            self.original = original
            self.capture = capture

        def write(self, data):
            self.original.write(data)
            self.capture.write(data)

        def flush(self):
            self.original.flush()
            self.capture.flush()

    sys.stdout = TeeStream(original_stdout, log_capture)
    sys.stderr = TeeStream(original_stderr, log_capture)

    try:
        print('[DEBUG] Chat endpoint called')
        print('CHAT:', current_user)

        if current_user.is_admin or current_user.chat_access:
            pass
        else:
            data = request.json
            catalog_id = data.get('catalogId', '')

            if catalog_id:
                catalog_permission = CatalogPermission.query.filter_by(
                    catalog_id=catalog_id,
                    user_id=current_user.id
                ).first()

                if not catalog_permission or catalog_permission.permission == PermissionType.READ_ONLY:
                    sys.stdout = original_stdout
                    sys.stderr = original_stderr
                    return jsonify({"error": "Chat access required"}), 403
            else:
                sys.stdout = original_stdout
                sys.stderr = original_stderr
                return jsonify({"error": "Chat access required"}), 403

        try:
            data = request.json
            user_message = data.get('message', '')
            catalog = data.get('catalogId', '')
            print(f'[DEBUG] Chat request - user_message: {user_message[:100]}..., catalog: {catalog}')

            if not user_message:
                print('[DEBUG] Empty message provided')
                sys.stdout = original_stdout
                sys.stderr = original_stderr
                return jsonify({"error": "El mensaje no puede estar vacío"}), 400

            user_id = current_user.id
            jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')
            print(f'[DEBUG] Processing chat for user_id: {user_id}')

            client_ip = request.environ.get('HTTP_X_FORWARDED_FOR')
            if client_ip:
                client_ip = client_ip.split(',')[0].strip()
            else:
                client_ip = request.environ.get('REMOTE_ADDR', 'unknown')
            print('CHAT IP: ', client_ip)

            print(f'[DEBUG] About to call generate_ai_response')
            ai_response, message_id, citations = generate_ai_response(user_message, catalog, user_id, jwt_token, client_ip)
            print(f'[DEBUG] generate_ai_response completed successfully, message_id: {message_id}, citations: {len(citations)}')

            print(f'[DEBUG] About to create activity log')
            create_activity_chat_log(EventType.CHAT_INTERACTION, current_user.email, catalog, message_id, 'spoke to the ai')
            print(f'[DEBUG] Activity log created successfully')

            print(f'[DEBUG] Chat endpoint returning response with {len(ai_response)} characters and {len(citations)} citations')

            sys.stdout = original_stdout
            sys.stderr = original_stderr

            return jsonify({
                "response": ai_response,
                "citations": citations,
                "message_id": message_id,
                "timestamp": None
            })
        except Exception as e:
            print(f'[ERROR] Chat endpoint error: {e}')
            tb.print_exc()

            sys.stdout = original_stdout
            sys.stderr = original_stderr

            return jsonify({
                "error": "Error interno del servidor"
            }), 500
    finally:
        sys.stdout = original_stdout
        sys.stderr = original_stderr

@app.route('/api/download-citation', methods=['POST'])
@token_required
def download_citation(current_user=None, token_user_data=None, **kwargs):
    try:
        from crypto_utils import decrypt_triplet
        from flask import send_file
        import tempfile

        data = request.json
        message_id = data.get('message_id')
        encrypted_triplet = data.get('encrypted_triplet')

        if not message_id or not encrypted_triplet:
            return jsonify({"error": "message_id and encrypted_triplet required"}), 400

        message = Message.query.join(Conversation).filter(
            Message.id == message_id,
            Conversation.speaker_id == current_user.id
        ).first()

        if not message:
            return jsonify({"error": "Message not found or access denied"}), 404

        if not message.encryption_key:
            return jsonify({"error": "No encryption key for this message"}), 400

        catalog_id, file_id, version_id = decrypt_triplet(encrypted_triplet, message.encryption_key)

        if not catalog_id or not file_id or not version_id:
            return jsonify({"error": "Invalid encrypted triplet"}), 400

        version = Version.query.join(File).join(Catalog).filter(
            Version.id == version_id,
            File.id == file_id,
            Catalog.id == catalog_id
        ).first()

        if not version:
            return jsonify({"error": "File version not found"}), 404

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

        return send_file(
            io.BytesIO(file_content),
            as_attachment=True,
            download_name=version.filename
        )

    except Exception as e:
        print(f"Error downloading citation file: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Error downloading file"}), 500

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
def upload_logo_endpoint(current_user=None, token_user_data=None, **kwargs):
    """Upload and resize company logo"""
    return upload_logo()

@app.route('/api/logo', methods=['GET'])
def get_logo_endpoint():
    """Retrieve company logo"""
    return get_logo()

@app.route('/api/activity-logs', methods=['GET'])
@admin_required
def get_activity_logs(current_user=None, token_user_data=None, **kwargs):
    """Get activity logs with pagination"""
    return get_activity_logs_with_pagination()

@app.route('/api/simple-mode', methods=['GET'])
@token_required
def get_simple_mode(current_user=None, token_user_data=None, **kwargs):
    """Get simple mode parameter based on user permissions and referer"""

    referer = request.headers.get('Referer', '')
    allowed_referers = [
        'https://sapientum-app.3htp.cloud/',
        'http://localhost:5173',
        'http://localhost:8000'
    ]

    is_allowed_referer = any(referer.startswith(ref) for ref in allowed_referers)

    if not is_allowed_referer:
        return jsonify({"simple_mode": True})

    if current_user.is_admin or current_user.is_catalog_editor:
        return jsonify({"simple_mode": False})

    has_catalog_permissions = CatalogPermission.query.filter_by(user_id=current_user.id).filter(
        CatalogPermission.permission != PermissionType.CHAT_ONLY
    ).first() is not None

    if has_catalog_permissions:
        return jsonify({"simple_mode": False})

    if current_user.chat_access:
        return jsonify({"simple_mode": True})

    return jsonify({"simple_mode": True})

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

def load_parameters():
    """Load parameters from database into memory"""
    global app_parameters
    try:
        with app.app_context():
            parameters = Parameter.query.all()
            app_parameters = {param.name: param.value for param in parameters}
            print(f"Loaded {len(app_parameters)} parameters into memory")
    except Exception as e:
        print(f"Error loading parameters: {e}")
        app_parameters = {}

with app.app_context():
    try:
        if db_utils.test_connection(app):
            print("Database connection test successful")
            load_parameters()
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
