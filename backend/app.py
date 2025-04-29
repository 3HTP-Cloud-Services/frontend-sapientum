from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
import os
import json
from catalog import get_all_catalogs, get_catalog_by_id, get_catalog_users
from auth import (
    authenticate_user, 
    get_user_role, 
    get_all_users, 
    get_user_by_id, 
    update_user_in_dynamo, 
    create_user_in_dynamo, 
    delete_user_from_dynamo
)

current_dir = os.path.dirname(os.path.abspath(__file__))
static_folder = os.path.join(current_dir, 'static')

app = Flask(__name__, static_folder=static_folder)
app.secret_key = os.urandom(24)
CORS(app, supports_credentials=True)

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
    
    user, error_message = authenticate_user(email, password)
    
    if user:
        session['logged_in'] = True
        session['user_email'] = email
        session['user_role'] = user.get('role')
        
        return jsonify({
            "success": True,
            "role": user.get('role')
        })
    
    if error_message == "Unknown User":
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
    
    catalogs = get_all_catalogs()
    return jsonify(catalogs)

@app.route('/api/documents', methods=['GET'])
def get_documents():
    # Redirect to catalogs for backward compatibility
    return get_catalogs()

@app.route('/api/catalogs/<string:catalog_id>', methods=['GET'])
def get_catalog(catalog_id):
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401
    
    catalog = get_catalog_by_id(catalog_id)
    if catalog:
        return jsonify(catalog)
    
    return jsonify({"error": "Catálogo no encontrado"}), 404

@app.route('/api/documents/<path:doc_id>', methods=['GET'])
def get_document(doc_id):
    # Redirect to get_catalog for backward compatibility
    return get_catalog(doc_id)

@app.route('/api/catalogs/<string:catalog_id>/users', methods=['GET'])
def get_users_for_catalog(catalog_id):
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401
    
    users = get_catalog_users(catalog_id)
    return jsonify(users)

@app.route('/api/catalogs/<string:catalog_id>/files', methods=['GET'])
def get_files_for_catalog(catalog_id):
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401
    
    files = [
        {
            "id": 1,
            "name": "Manual_IT.pdf",
            "size": "2.4 MB",
            "created_at": "2025-02-15T10:30:45Z"
        },
        {
            "id": 2,
            "name": "Manual_CRM.pdf",
            "size": "3.7 MB",
            "created_at": "2025-03-22T14:15:30Z"
        }
    ]
    
    return jsonify(files)

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
    
    users = get_all_users()
    return jsonify(users)

@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401
    
    user = get_user_by_id(user_id)
    if user:
        return jsonify(user)
    
    return jsonify({"error": "Usuario no encontrado"}), 404

@app.route('/api/users', methods=['POST'])
def create_user():
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401
    
    data = request.json
    if not data or not data.get('email'):
        return jsonify({"error": "El email es requerido"}), 400
    
    users = get_all_users()
    next_id = max([user['id'] for user in users]) + 1 if users else 1
    
    new_user = {
        "id": next_id,
        "original_username": data.get('email'),
        "email": data.get('email'),
        "documentAccess": data.get('documentAccess', 'Lectura'),
        "chatAccess": data.get('chatAccess', False),
        "isAdmin": data.get('isAdmin', False),
        "role": "admin" if data.get('isAdmin', False) else "user"
    }
    
    if create_user_in_dynamo(new_user):
        return jsonify(new_user), 201
    else:
        return jsonify({"error": "Error al crear usuario en DynamoDB"}), 500

@app.route('/api/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401
    
    data = request.json
    if not data:
        return jsonify({"error": "No se proporcionaron datos"}), 400
    
    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404
    
    for key in ['email', 'documentAccess', 'chatAccess', 'isAdmin']:
        if key in data:
            user[key] = data[key]
    
    user['role'] = 'admin' if user['isAdmin'] else 'user'
    
    if update_user_in_dynamo(user):
        return jsonify(user)
    else:
        return jsonify({"error": "Error al actualizar usuario en DynamoDB"}), 500

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401
    
    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404
    
    username = user.get('original_username') or user.get('email')
    
    if delete_user_from_dynamo(username):
        return jsonify({"success": True, "eliminado": user})
    else:
        return jsonify({"error": "Error al eliminar usuario de DynamoDB"}), 500

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

if __name__ == '__main__':
    # Check if we should run in static mode
    static_mode = os.environ.get('STATIC_MODE', 'false').lower() == 'true'
    if static_mode:
        print(f"Ejecutando en MODO ESTÁTICO - sirviendo archivos estáticos desde {static_folder}")
    
    print(f"Servidor ejecutándose en http://localhost:8000")
    app.run(debug=True, port=8000)