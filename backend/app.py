from flask import Flask, request, jsonify, session, send_from_directory, send_file, Response
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
import json
from models import db, User, Domain, CatalogPermission, Catalog, PermissionType, File, Version
import db as db_utils
import traceback
from datetime import datetime

current_dir = os.path.dirname(os.path.abspath(__file__))
static_folder = os.path.join(current_dir, 'static')

app = Flask(__name__, static_folder=static_folder)
app.secret_key = os.urandom(24)
CORS(app, supports_credentials=True)

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

DOCUMENTS = [
    {
        "id": 1,
        "title": "Procedimientos de Evaluación de Competencia de IA",
        "content": "Este documento describe métricas para medir el rendimiento de la IA incluyendo precisión, tiempo de respuesta y amplitud de conocimiento. El documento también analiza estrategias de implementación para diversos contextos organizacionales y mejores prácticas para evaluar la competencia de IA en diferentes dominios. La evaluación debe incluir tanto métricas cuantitativas como evaluaciones cualitativas."
    },
    {
        "id": 2,
        "title": "Estrategias de Implementación para Sistemas de IA",
        "content": "Este documento describe estrategias de implementación para sistemas de IA en varios contextos organizacionales, incluyendo mejores prácticas para despliegue e integración. Cubre consideraciones técnicas, gestión de partes interesadas y técnicas de mitigación de riesgos. El documento también proporciona un marco para evaluar la preparación organizacional para la adopción de IA."
    },
    {
        "id": 3,
        "title": "Casos de Estudio de Implementación de IA",
        "content": "Este documento proporciona casos de estudio de implementaciones exitosas de IA con análisis detallado de resultados y lecciones aprendidas. Cada caso de estudio examina los desafíos enfrentados, soluciones implementadas y resultados logrados. El documento concluye con patrones comunes y mejores prácticas derivadas de estos ejemplos del mundo real."
    }
]

def generate_ai_response(user_query):
    responses = {
        'hola': '¡Hola! ¿Cómo puedo ayudarte hoy?',
        'ayuda': 'Puedo ayudarte con resúmenes de documentos, responder preguntas sobre el sistema o proporcionar orientación sobre la evaluación de competencia de IA.',
        'documento': '¿Qué documento te gustaría que resuma o proporcione información?',
        'resumir': 'Puedo resumir documentos para ti. Por favor, especifica qué documento te gustaría que resuma.',
        'permisos': 'Los permisos de usuario son administrados por los administradores. Hay diferentes niveles de acceso para documentos y funcionalidad de chat.',
        'hello': '¡Hola! ¿Cómo puedo ayudarte hoy?',
        'help': 'Puedo ayudarte con resúmenes de documentos, responder preguntas sobre el sistema o proporcionar orientación sobre la evaluación de competencia de IA.',
    }

    doc_responses = {}
    for doc in DOCUMENTS:
        doc_id = str(doc['id'])
        doc_title = doc['title'].lower()
        doc_responses[f'document {doc_id}'] = f"{doc['title']} - {doc['content'][:150]}..."
        doc_responses[doc_title] = f"{doc['title']} - {doc['content'][:150]}..."

    all_responses = {**responses, **doc_responses}

    lower_query = user_query.lower()

    for keyword, response in all_responses.items():
        if keyword in lower_query:
            return response

    for doc in DOCUMENTS:
        title_words = doc['title'].lower().split()
        for word in title_words:
            if len(word) > 3 and word in lower_query:
                return f"Encontré un documento que podría interesarte: {doc['title']} - {doc['content'][:100]}..."

    return "No estoy seguro de entender tu pregunta. ¿Podrías reformularla o proporcionar más detalles?"

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('username')
    password = data.get('password')

    # NOTE: We're using a hardcoded password here for development
    # In production, you would use proper password hashing and authentication
    # We're keeping this simple for the example
    user = User.query.filter_by(email=email).first()

    if user and password == "user123":  # Hardcoded password check for simplicity
        session['logged_in'] = True
        session['user_email'] = email
        session['user_role'] = user.role

        return jsonify({
            "success": True,
            "role": user.role
        })

    if not user:
        return jsonify({"success": False, "message": "Unknown User"}), 401

    return jsonify({"success": False, "message": "Credenciales inválidas"}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('logged_in', None)
    session.pop('user_email', None)
    session.pop('user_role', None)
    return jsonify({"success": True})

@app.route('/api/check-auth', methods=['GET'])
def check_auth():
    if session.get('logged_in'):
        return jsonify({
            "authenticated": True,
            "email": session.get('user_email'),
            "role": session.get('user_role')
        })
    return jsonify({"authenticated": False}), 401

@app.route('/api/allowed-domains', methods=['PUT'])
def allowed_domains():
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401

    user_email = session.get('user_email')
    user = User.query.filter_by(email=user_email).first()
    if not user or not user.is_admin:
        return jsonify({"error": "Acceso denegado. Se requieren permisos de administrador."}), 403

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
def delete_domain(domain_id):
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401

    user_email = session.get('user_email')
    user = User.query.filter_by(email=user_email).first()
    if not user or not user.is_admin:
        return jsonify({"error": "Acceso denegado. Se requieren permisos de administrador."}), 403

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

@app.route('/api/i18n', methods=['POST'])
def update_translations():
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401

    data = request.json
    if not data:
        return jsonify({"error": "No se proporcionaron datos"}), 400

    if 'language' not in data or 'updates' not in data:
        return jsonify({"error": "Se requiere 'language' y 'updates'"}), 400

    language = data['language']
    updates = data['updates']

    if language not in TRANSLATIONS:
        return jsonify({"error": f"Idioma '{language}' no soportado"}), 400

    for key, value in updates.items():
        if key in TRANSLATIONS[language]:
            TRANSLATIONS[language][key] = value
        else:
            return jsonify({"error": f"Clave de traducción '{key}' no encontrada"}), 400

    return jsonify({"success": True, "message": "Traducciones actualizadas correctamente"})

@app.route('/api/catalogs', methods=['GET'])
def get_catalogs():
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401

    from catalog import get_all_catalogs
    catalogs = get_all_catalogs()
    return jsonify(catalogs)

@app.route('/api/catalogs', methods=['POST'])
def create_catalog():
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401

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
def get_types():
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401

    from catalog import get_catalog_types
    catalog_types = get_catalog_types()
    return jsonify(catalog_types)

@app.route('/api/documents', methods=['GET'])
def get_documents():
    return get_catalogs()

@app.route('/api/catalogs/<int:catalog_id>', methods=['GET'])
def get_catalog(catalog_id):
    print('catalog_id:', catalog_id)
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401

    catalog = Catalog.query.get(catalog_id)
    if catalog:
        return jsonify(catalog.to_dict())

    return jsonify({"error": "Catálogo no encontrado"}), 404

@app.route('/api/documents/<path:doc_id>', methods=['GET'])
def get_document(doc_id):
    return get_catalog(doc_id)

@app.route('/api/catalogs/<string:catalog_id>/users', methods=['GET'])
def get_users_for_catalog(catalog_id):
    print('get_users_for_catalog:', catalog_id)
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401

    # Check if user is admin
    user_email = session.get('user_email')
    user = User.query.filter_by(email=user_email).first()
    if not user or not user.is_admin:
        return jsonify({"error": "Acceso denegado. Se requieren permisos de administrador."}), 403

    catalog_users = CatalogPermission.query.filter_by(catalog_id=catalog_id).all()
    users = []

    for cu in catalog_users:
        user = User.query.get(cu.user_id)
        if user:
            user_data = user.to_dict()
            user_data['permission'] = cu.permission.value
            users.append(user_data)

    return jsonify(users)

@app.route('/api/catalogs/<string:catalog_id>/available-users', methods=['GET'])
def get_available_users_for_catalog(catalog_id):
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401

    # Check if user is admin
    user_email = session.get('user_email')
    user = User.query.filter_by(email=user_email).first()
    if not user or not user.is_admin:
        return jsonify({"error": "Acceso denegado. Se requieren permisos de administrador."}), 403

    existing_users_query = db.session.query(CatalogPermission.user_id).filter(CatalogPermission.catalog_id == catalog_id)
    existing_user_ids = [user_id for (user_id,) in existing_users_query]

    available_users = User.query.filter(User.is_active == True, ~User.id.in_(existing_user_ids)).all()

    return jsonify([user.to_dict() for user in available_users])

@app.route('/api/catalogs/<string:catalog_id>/users', methods=['POST'])
def add_user_to_catalog(catalog_id):
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401

    # Check if user is admin
    user_email = session.get('user_email')
    user = User.query.filter_by(email=user_email).first()
    if not user or not user.is_admin:
        return jsonify({"error": "Acceso denegado. Se requieren permisos de administrador."}), 403

    data = request.json
    if not data or 'user_id' not in data or 'permission' not in data:
        return jsonify({"error": "Se requiere user_id y permission"}), 400

    user_id = data['user_id']
    permission_value = data['permission']

    try:
        permission_type = PermissionType(permission_value)
    except ValueError:
        return jsonify({"error": f"Valor de permiso inválido: {permission_value}"}), 400

    try:
        existing_permission = CatalogPermission.query.filter_by(
            catalog_id=catalog_id,
            user_id=user_id
        ).first()

        if existing_permission:
            existing_permission.permission = permission_type
        else:
            new_permission = CatalogPermission(
                catalog_id=catalog_id,
                user_id=user_id,
                permission=permission_type
            )
            db.session.add(new_permission)

        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Error al guardar permisos: {str(e)}"}), 500

@app.route('/api/catalogs/<string:catalog_id>/users/<int:user_id>', methods=['DELETE'])
def remove_user_from_catalog(catalog_id, user_id):
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401

    # Check if user is admin
    user_email = session.get('user_email')
    user = User.query.filter_by(email=user_email).first()
    if not user or not user.is_admin:
        return jsonify({"error": "Acceso denegado. Se requieren permisos de administrador."}), 403

    try:
        permission = CatalogPermission.query.filter_by(
            catalog_id=catalog_id,
            user_id=user_id
        ).first()

        if not permission:
            return jsonify({"error": "Permiso no encontrado"}), 404

        db.session.delete(permission)
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Error al eliminar permiso: {str(e)}"}), 500

@app.route('/api/catalogs/<string:catalog_id>/files', methods=['GET'])
def get_files_for_catalog(catalog_id):
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401

    from catalog import get_catalog_files
    files = get_catalog_files(catalog_id)
    return jsonify(files)


@app.route('/api/catalogs/<string:catalog_id>/upload', methods=['POST'])
def upload_file_to_catalog(catalog_id):
    print(f"[DEBUG] Starting upload to catalog {catalog_id}")

    if not session.get('logged_in'):
        print(f"[DEBUG] Auth failed - not logged in")
        return jsonify({"error": "No autorizado"}), 401

    print(f"[DEBUG] User authenticated: {session.get('user_id')}")
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
def upload_new_version(file_id):
    print("Starting upload_new_version function")

    if not session.get('logged_in'):
        print("User is not logged in")
        return jsonify({"error": "No autorizado"}), 401

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

        user_email = session.get('user_email')
        print(f"Fetching user by email: {user_email}")
        user = User.query.filter_by(email=user_email).first()
        user_id = user.id if user else None

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
def update_file(file_id):
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401

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
def download_file(file_id):
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401

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
                    "Content-Disposition": f"attachment; filename={filename}"
                }
            )
        except Exception as e:
            return jsonify({"error": f"Error retrieving file from S3: {str(e)}"}), 500

    except Exception as e:
        return jsonify({"error": f"Error downloading file: {str(e)}"}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401

    data = request.json
    user_message = data.get('message', '')

    if not user_message:
        return jsonify({"error": "El mensaje no puede estar vacío"}), 400

    ai_response = generate_ai_response(user_message)

    return jsonify({
        "response": ai_response,
        "timestamp": None
    })

@app.route('/api/users', methods=['GET'])
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

@app.route('/api/users/<int:user_id>', methods=['GET'])
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

@app.route('/api/users', methods=['POST'])
def create_user():
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401

    # Check if user is admin
    user_email = session.get('user_email')
    current_user = User.query.filter_by(email=user_email).first()
    if not current_user or not current_user.is_admin:
        return jsonify({"error": "Acceso denegado. Se requieren permisos de administrador."}), 403

    data = request.json
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

@app.route('/api/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401

    # Check if user is admin
    user_email = session.get('user_email')
    current_user = User.query.filter_by(email=user_email).first()
    if not current_user or not current_user.is_admin:
        return jsonify({"error": "Acceso denegado. Se requieren permisos de administrador."}), 403

    data = request.json
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

@app.route('/api/users/<int:user_id>/toggle/<string:property>', methods=['PUT'])
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

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
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

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_static_files(path):
    static_mode = os.environ.get('STATIC_MODE', 'false').lower() == 'true'

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
    static_mode = os.environ.get('STATIC_MODE', 'false').lower() == 'true'
    if static_mode:
        print(f"Ejecutando en MODO ESTÁTICO - sirviendo archivos estáticos desde {static_folder}")

    print(f"Servidor ejecutándose en http://localhost:8000")
    app.run(debug=True, port=8000)