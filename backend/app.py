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
from auth_decorator import token_required, admin_required, chat_access_required

from catalog import get_all_catalogs

current_dir = os.path.dirname(os.path.abspath(__file__))
static_folder = os.path.join(current_dir, 'static')

app = Flask(__name__, static_folder=static_folder)

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
    # Running locally, enable Flask CORS
    cors = CORS(
        app,
        supports_credentials=True,
        resources={
            "/*": {
                "origins": "*",
                "allow_headers": ["Content-Type", "Authorization", "Accept"],
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

@app.route('/api/check-auth', methods=['GET'])
def check_auth():
    from auth_decorator import token_required
    from cognito import get_user_from_token
    
    success, user_data = get_user_from_token()
    
    if not success:
        return jsonify({"authenticated": False, "error": user_data.get("error")}), 401
    
    # Token authentication successful
    embedded = is_embedded_request()
    return jsonify({
        "authenticated": True,
        "email": user_data.get("email"),
        "role": user_data.get("role"),
        "is_embedded": embedded,
        "is_admin": user_data.get("is_admin"),
        "chat_access": user_data.get("chat_access")
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
        domain = Domain.query.get(domain_id)
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
    catalogs = get_all_catalogs(user=current_user)
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

    catalog = Catalog.query.get(catalog_id)
    if catalog:
        return jsonify(catalog.to_dict())

    return jsonify({"error": "Catálogo no encontrado"}), 404

@app.route('/api/documents/<path:doc_id>', methods=['GET'])
def get_document(doc_id):
    return get_catalog(doc_id)

@app.route('/api/catalogs/<string:catalog_id>/users', methods=['GET'])
@admin_required
def get_users_for_catalog(catalog_id, current_user=None, token_user_data=None, **kwargs):
    print('get_users_for_catalog:', catalog_id)

    from catalog import get_catalog_users
    users = get_catalog_users(catalog_id)
    return jsonify(users)

@app.route('/api/catalogs/<string:catalog_id>/available-users', methods=['GET'])
@admin_required
def get_available_users_for_catalog(catalog_id, current_user=None, token_user_data=None, **kwargs):
    from catalog import get_available_users_for_catalog as get_available_users
    available_users = get_available_users(catalog_id)
    return jsonify(available_users)

@app.route('/api/catalogs/<string:catalog_id>/users', methods=['POST'])
@admin_required
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
@admin_required
def remove_user_from_catalog(catalog_id, user_id, current_user=None, token_user_data=None, **kwargs):
    from catalog import remove_user_from_catalog as remove_user
    result = remove_user(catalog_id, user_id)

    # Check if result is a tuple containing an error message and status code
    if isinstance(result, tuple) and len(result) == 2 and isinstance(result[0], dict) and 'error' in result[0]:
        return jsonify(result[0]), result[1]

    return jsonify(result)

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
        file = File.query.get(file_id)
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

        catalog = Catalog.query.get(file.catalog_id)
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
        file = File.query.get(file_id)
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
        file = File.query.get(file_id)
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
        encoded_filename = quote(filename.encode('utf-8'))
        s3_client = get_client_with_assumed_role('s3')

        try:
            s3_response = s3_client.get_object(
                Bucket=bucket_name,
                Key=s3_key
            )

            file_content = s3_response['Body'].read()

            return Response(
                file_content,
                mimetype=s3_response.get('ContentType', 'application/octet-stream'),
                headers={
                    "Content-Disposition": f"attachment; filename={encoded_filename}"
                }
            )
        except Exception as e:
            traceback.print_exc()
            return jsonify({"error": f"Error retrieving file from S3: {str(e)}"}), 500

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Error downloading file: {str(e)}"}), 500

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
    create_activity_chat_log(EventType.CHAT_INTERACTION, user_id, catalog, message_id, 'spoke to the ai')

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
    from users import create_user as create_new_user
    return create_new_user(request.json, current_user=current_user)

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
            log_dict = {
                'id': log.id,
                'activity': log.activity,
                'message': log.message,
                'event': log.event.value if log.event else None,
                'user_id': log.user_id,
                'other_user_id': log.other_user_id,
                'created_at': log.created_at.isoformat() if log.created_at else None,
                'catalog_id': log.catalog_id,
                'file_id': log.file_id,
                'version_id': log.version_id,
                'message_id': log.message_id
            }

            # Add user email
            user = User.query.get(log.user_id)
            if user:
                log_dict['user_email'] = user.email

            # Add other user email if present
            if log.other_user_id:
                other_user = User.query.get(log.other_user_id)
                if other_user:
                    log_dict['other_user_email'] = other_user.email

            # Add catalog name if present
            if log.catalog_id:
                catalog = Catalog.query.get(log.catalog_id)
                if catalog:
                    log_dict['catalog_name'] = catalog.name

            # Add file name if present
            if log.file_id:
                file = File.query.get(log.file_id)
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
