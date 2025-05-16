# Svelte 5 + Flask App

A simple document management application with authentication, built with Svelte 5 frontend and Flask backend.


## Setup Instructions

### Backend Setup

1. Navigate to the backend directory:
   ```
   cd backend
   ```

2. Create a virtual environment (optional but recommended):
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Run the Flask server:
   ```
   python app.py
   ```
   The backend will run at http://localhost:8000
   
   By default, static files are served from the static folder. If you want to disable static file serving, set the environment variable:
   ```
   export STATIC_MODE=false
   ```

### Running on EC2 or Another AWS Service

When running on an EC2 instance or another AWS service with an IAM role attached:

1. Set the `EC2_ROLE` environment variable to `true`:
   ```
   export EC2_ROLE=true
   ```
   
   You can also add this to your startup script or systemd service file:
   ```
   Environment="EC2_ROLE=true"
   ```

2. Make sure the IAM role attached to your EC2 instance has the necessary permissions:
   - SecretsManager access to read database credentials
   - S3 access for file storage
   - Any other AWS services your application uses

This configuration tells the application to use the instance profile credentials instead of trying to assume a role.

### Frontend Setup

1. Navigate to the frontend directory:
   ```
   cd frontend
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Run the development server:
   ```
   npm run dev
   ```
   The frontend will run at http://localhost:5173

## Usage

1. Access the application at http://localhost:5173
2. Login with username: `user` and password: `user123`
3. Browse the document list and view document details

## API Endpoints

- `POST /api/login` - Login with username and password
- `POST /api/logout` - Logout current user
- `GET /api/check-auth` - Check if user is authenticated
- `GET /api/documents` - Get list of documents
- `GET /api/documents/<id>` - Get document by ID
