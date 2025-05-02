from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
import json
from models import db, User, Domain
import db as db_utils

current_dir = os.path.dirname(os.path.abspath(__file__))
static_folder = os.path.join(current_dir, 'static')

app = Flask(__name__, static_folder=static_folder)
app.secret_key = os.urandom(24)
CORS(app, supports_credentials=True)

# Configure the Flask app with database settings
db_config = db_utils.get_db_config()
app.config.update(db_config)

# Initialize SQLAlchemy with the Flask app
db.init_app(app)

# Initialize Flask-Migrate
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
        print('nani?')
        return jsonify({"error": "No autorizado"}), 401

    data = request.json
    print('allowed_domains', data)
    if not data or not data.get('domains'):
        return jsonify({"error": "El campo 'domains' es requerido"}), 400

    try:
        new_domains = data['domains']
        existing_domains = Domain.query.all()
        existing_domain_map = {d.id: d for d in existing_domains}

        # Update existing domains or add new ones
        for domain_data in new_domains:
            print('new domain', domain_data)
            if 'id' in domain_data and domain_data['id'] in existing_domain_map:
                # Update existing domain
                print('if')
                domain = existing_domain_map[domain_data['id']]
                domain.name = domain_data['name']
            else:
                print('else', domain_data['name'])
                # Add new domain
                new_domain = Domain(name=domain_data['name'])
                print('new domain', new_domain)
                db.session.add(new_domain)

        db.session.commit()
        return jsonify({"success": True, "message": "Dominios actualizados correctamente"})
    except Exception as e:
        db.session.rollback()
        print(f"Error saving domains: {e}")
        return jsonify({"error": "Error al guardar dominios en la base de datos"}), 500


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
    catalogs = []
    # catalogs = Catalog.query.all()
    return jsonify([catalog.to_dict() for catalog in catalogs])

@app.route('/api/catalog-types', methods=['GET'])
def get_types():
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401
    
    # This is now hardcoded but could be stored in the database
    catalog_types = ['general', 'technical', 'business', 'other']
    return jsonify(catalog_types)

@app.route('/api/documents', methods=['GET'])
def get_documents():
    # Redirect to catalogs for backward compatibility
    return get_catalogs()

@app.route('/api/catalogs/<string:catalog_id>', methods=['GET'])
def get_catalog(catalog_id):
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401
    
    catalog = Catalog.query.get(catalog_id)
    if catalog:
        return jsonify(catalog.to_dict())
    
    return jsonify({"error": "Catálogo no encontrado"}), 404

@app.route('/api/documents/<path:doc_id>', methods=['GET'])
def get_document(doc_id):
    # Redirect to get_catalog for backward compatibility
    return get_catalog(doc_id)

@app.route('/api/catalogs/<string:catalog_id>/users', methods=['GET'])
def get_users_for_catalog(catalog_id):
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401
    
    catalog_users = CatalogUser.query.filter_by(catalog_id=catalog_id).all()
    users = []
    
    for cu in catalog_users:
        user = User.query.get(cu.user_id)
        if user:
            user_data = user.to_dict()
            user_data['permissions'] = cu.permissions
            users.append(user_data)
    
    return jsonify(users)

@app.route('/api/catalogs/<string:catalog_id>/files', methods=['GET'])
def get_files_for_catalog(catalog_id):
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401
    
    files = CatalogFile.query.filter_by(catalog_id=catalog_id).all()
    return jsonify([file.to_dict() for file in files])

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
        "timestamp": None  # Frontend will set the timestamp
    })

@app.route('/api/users', methods=['GET'])
def get_users():
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401
    
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
    
    user = User.query.get(user_id)
    if user:
        return jsonify(user.to_dict())
    
    return jsonify({"error": "Usuario no encontrado"}), 404

@app.route('/api/users', methods=['POST'])
def create_user():
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401
    
    data = request.json
    if not data or not data.get('email'):
        return jsonify({"error": "El email es requerido"}), 400
    
    # Check if user already exists
    existing_user = User.query.filter_by(email=data.get('email')).first()
    if existing_user:
        return jsonify({"error": "El email ya está en uso"}), 400
    
    # Create new user
    new_user = User(
        email=data.get('email'),
        original_username=data.get('email'),
        document_access=data.get('documentAccess', 'Lectura'),
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
    
    data = request.json
    if not data:
        return jsonify({"error": "No se proporcionaron datos"}), 400
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404
    
    # Update user fields
    if 'email' in data:
        user.email = data['email']
    
    if 'documentAccess' in data:
        user.document_access = data['documentAccess']
    
    if 'chatAccess' in data:
        user.chat_access = data['chatAccess']
    
    if 'isAdmin' in data:
        user.is_admin = data['isAdmin']
        user.role = 'admin' if data['isAdmin'] else 'user'
    
    try:
        db.session.commit()
        return jsonify(user.to_dict())
    except Exception as e:
        db.session.rollback()
        print(f"Error updating user: {e}")
        return jsonify({"error": "Error al actualizar usuario en la base de datos"}), 500

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404
    
    try:
        deleted_user = user.to_dict()  # Save user data before deletion
        db.session.delete(user)
        db.session.commit()
        return jsonify({"success": True, "eliminado": deleted_user})
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting user: {e}")
        return jsonify({"error": "Error al eliminar usuario de la base de datos"}), 500

# Catch-all route for serving static files in static mode
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_static_files(path):
    # Only handle this route if STATIC_MODE is enabled
    static_mode = os.environ.get('STATIC_MODE', 'false').lower() == 'true'
    
    if not static_mode:
        return jsonify({"error": "No encontrado"}), 404
    
    # Debug info
    print(f"Static mode request path: {path}")
    
    try:
        # Special case for the root path - always serve index.html
        if not path:
            print("Serving index.html for root path")
            return send_from_directory(app.static_folder, 'index.html')
        
        # Handle API requests normally - let them go to their API routes
        if path.startswith('api/'):
            print(f"API request: {path}, letting Flask routes handle it")
            # Don't do anything, let the other routes handle this
            return jsonify({"error": "Endpoint de API no encontrado"}), 404
            
        # For non-API paths, try to serve a static file
        file_path = os.path.join(app.static_folder, path)
        if os.path.isfile(file_path):
            print(f"Serving static file: {path}")
            return send_from_directory(app.static_folder, path)
        
        # If no file found, serve index.html for SPA routing
        print(f"No static file found for {path}, serving index.html")
        return send_from_directory(app.static_folder, 'index.html')
    except Exception as e:
        print(f"Error serving file: {str(e)}")
        return f"Error: {str(e)}", 500

# Test database connection
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
        
        # Create a default admin user
        admin = User(
            email="admin@example.com",
            original_username="admin@example.com",
            document_access="Lectura/Escritura",
            chat_access=True,
            is_admin=True,
            role="admin"
        )
        
        # Create a default regular user
        user = User(
            email="user@example.com",
            original_username="user@example.com",
            document_access="Lectura",
            chat_access=True,
            is_admin=False,
            role="user"
        )
        
        # Create a test catalog
        catalog = Catalog(
            id="test-catalog",
            name="Test Catalog",
            description="This is a test catalog",
            type="general"
        )
        
        # Add admin to the catalog with read/write permissions
        catalog_user = CatalogUser(
            catalog_id=catalog.id,
            user_id=1,  # This will be admin's ID
            permissions="read/write"
        )
        
        db.session.add(admin)
        db.session.add(user)
        db.session.add(catalog)
        db.session.commit()  # Commit to get IDs for admin and user
        
        db.session.add(catalog_user)
        db.session.commit()
        
        print("Default data seeded successfully")
        return True
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False

if __name__ == '__main__':
    # Check if we should run in static mode
    static_mode = os.environ.get('STATIC_MODE', 'false').lower() == 'true'
    if static_mode:
        print(f"Ejecutando en MODO ESTÁTICO - sirviendo archivos estáticos desde {static_folder}")
    
    print(f"Servidor ejecutándose en http://localhost:8000")
    app.run(debug=True, port=8000)