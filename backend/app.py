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

# Mock documents data
DOCUMENTS = [
    {"id": 1, "title": "Document 1", "content": "This is document 1 content."},
    {"id": 2, "title": "Document 2", "content": "This is document 2 content."},
    {"id": 3, "title": "Document 3", "content": "This is document 3 content."}
]

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if username == USER['username'] and password == USER['password']:
        session['logged_in'] = True
        return jsonify({"success": True})
    
    return jsonify({"success": False, "message": "Invalid credentials"}), 401

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
        return jsonify({"error": "Unauthorized"}), 401
    
    return jsonify(DOCUMENTS)

@app.route('/api/documents/<int:doc_id>', methods=['GET'])
def get_document(doc_id):
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
    
    for doc in DOCUMENTS:
        if doc['id'] == doc_id:
            return jsonify(doc)
    
    return jsonify({"error": "Document not found"}), 404

# Catch-all route for serving static files in static mode
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_static_files(path):
    # Only handle this route if STATIC_MODE is enabled
    static_mode = os.environ.get('STATIC_MODE', 'false').lower() == 'true'
    
    if not static_mode:
        return jsonify({"error": "Not found"}), 404
    
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
            return jsonify({"error": "API endpoint not found"}), 404
            
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
        print(f"Running in STATIC MODE - serving static files from {static_folder}")
    
    print(f"Server running at http://localhost:8000")
    app.run(debug=True, port=8000)