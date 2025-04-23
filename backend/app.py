from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
import os

# Get the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))
# Path to static folder - will be used when serving static files
static_folder = os.path.join(current_dir, 'static')

# Initialize Flask app - can switch between API mode and static mode
app = Flask(__name__, static_folder=static_folder)
app.secret_key = os.urandom(24)
CORS(app, supports_credentials=True)

# Hardcoded user for now
USER = {
    "username": "user",
    "password": "user123"
}

# Users with permissions
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

# Mock documents data
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

# AI chat responses
def generate_ai_response(user_query):
    # Mock AI response based on user query
    responses = {
        'hola': '¡Hola! ¿Cómo puedo ayudarte hoy?',
        'ayuda': 'Puedo ayudarte con resúmenes de documentos, responder preguntas sobre el sistema o proporcionar orientación sobre la evaluación de competencia de IA.',
        'documento': '¿Qué documento te gustaría que resuma o proporcione información?',
        'resumir': 'Puedo resumir documentos para ti. Por favor, especifica qué documento te gustaría que resuma.',
        'permisos': 'Los permisos de usuario son administrados por los administradores. Hay diferentes niveles de acceso para documentos y funcionalidad de chat.',
        'hello': '¡Hola! ¿Cómo puedo ayudarte hoy?',
        'help': 'Puedo ayudarte con resúmenes de documentos, responder preguntas sobre el sistema o proporcionar orientación sobre la evaluación de competencia de IA.',
    }
    
    # Create responses based on actual document data
    doc_responses = {}
    for doc in DOCUMENTS:
        doc_id = str(doc['id'])
        doc_title = doc['title'].lower()
        # Add response for document by ID
        doc_responses[f'document {doc_id}'] = f"{doc['title']} - {doc['content'][:150]}..."
        # Add response for document by title
        doc_responses[doc_title] = f"{doc['title']} - {doc['content'][:150]}..."
    
    # Merge the two dictionaries
    all_responses = {**responses, **doc_responses}
    
    # Check if query contains any keywords
    lower_query = user_query.lower()
    
    # First check for exact matches
    for keyword, response in all_responses.items():
        if keyword in lower_query:
            return response
    
    # Then check for partial matches on document titles
    for doc in DOCUMENTS:
        title_words = doc['title'].lower().split()
        for word in title_words:
            if len(word) > 3 and word in lower_query:  # Only match on words longer than 3 chars
                return f"Encontré un documento que podría interesarte: {doc['title']} - {doc['content'][:100]}..."
    
    # Default response
    return "No estoy seguro de entender tu pregunta. ¿Podrías reformularla o proporcionar más detalles?"

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if username == USER['username'] and password == USER['password']:
        session['logged_in'] = True
        return jsonify({"success": True})
    
    return jsonify({"success": False, "message": "Credenciales inválidas"}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('logged_in', None)
    return jsonify({"success": True})

@app.route('/api/check-auth', methods=['GET'])
def check_auth():
    if session.get('logged_in'):
        return jsonify({"authenticated": True})
    return jsonify({"authenticated": False}), 401

@app.route('/api/documents', methods=['GET'])
def get_documents():
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401
    
    return jsonify(DOCUMENTS)

@app.route('/api/documents/<int:doc_id>', methods=['GET'])
def get_document(doc_id):
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401
    
    for doc in DOCUMENTS:
        if doc['id'] == doc_id:
            return jsonify(doc)
    
    return jsonify({"error": "Documento no encontrado"}), 404

@app.route('/api/chat', methods=['POST'])
def chat():
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401
    
    data = request.json
    user_message = data.get('message', '')
    
    if not user_message:
        return jsonify({"error": "El mensaje no puede estar vacío"}), 400
    
    # Generate response
    ai_response = generate_ai_response(user_message)
    
    return jsonify({
        "response": ai_response,
        "timestamp": None  # Frontend will set the timestamp
    })

@app.route('/api/users', methods=['GET'])
def get_users():
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401
    
    return jsonify(USERS)

@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401
    
    for user in USERS:
        if user['id'] == user_id:
            return jsonify(user)
    
    return jsonify({"error": "Usuario no encontrado"}), 404

@app.route('/api/users', methods=['POST'])
def create_user():
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401
    
    data = request.json
    if not data or not data.get('email'):
        return jsonify({"error": "El email es requerido"}), 400
    
    # Get the next available ID
    next_id = max([user['id'] for user in USERS]) + 1 if USERS else 1
    
    new_user = {
        "id": next_id,
        "email": data.get('email'),
        "documentAccess": data.get('documentAccess', 'Read'),
        "chatAccess": data.get('chatAccess', False),
        "isAdmin": data.get('isAdmin', False)
    }
    
    USERS.append(new_user)
    return jsonify(new_user), 201

@app.route('/api/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401
    
    data = request.json
    if not data:
        return jsonify({"error": "No se proporcionaron datos"}), 400
    
    for i, user in enumerate(USERS):
        if user['id'] == user_id:
            # Update user with provided fields
            for key in ['email', 'documentAccess', 'chatAccess', 'isAdmin']:
                if key in data:
                    USERS[i][key] = data[key]
            return jsonify(USERS[i])
    
    return jsonify({"error": "Usuario no encontrado"}), 404

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    if not session.get('logged_in'):
        return jsonify({"error": "No autorizado"}), 401
    
    for i, user in enumerate(USERS):
        if user['id'] == user_id:
            deleted_user = USERS.pop(i)
            return jsonify({"success": True, "eliminado": deleted_user})
    
    return jsonify({"error": "Usuario no encontrado"}), 404

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