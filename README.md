# Sapientum Application with Shared Components

This application consists of two separate frontends that share common components:

1. **Main Frontend** (port 5173) - Full application with all features
2. **Chat-only Frontend** (port 5573) - Streamlined interface with only chat functionality

Both frontends connect to the same backend API.
 
## Project Structure

```
/svelte_flask/
  /backend/                  # Flask backend API
  /frontend/                 # Main Svelte application
  /embed-frontend/           # Chat-only Svelte application
  /shared-components/        # Shared UI components and utilities
    /Header/                 # Shared header component
    /Login/                  # Shared login component
    /Chat/                   # Shared chat component
    /utils/                  # Shared utilities (auth, i18n)
```

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

### Main Frontend Setup

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
   The main frontend will run at http://localhost:5173

### Chat-only Frontend Setup

1. Navigate to the embed-frontend directory:
   ```
   cd embed-frontend
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Run the development server:
   ```
   npm run dev
   ```
   The chat-only frontend will run at http://localhost:5573

### Starting All Applications at Once

Use the provided script to start all applications:
```
./start-apps.sh
```

## Usage

1. Access the main application at http://localhost:5173
2. Access the chat-only application at http://localhost:5573
3. Login with username: `user` and password: `user123`

## Embedding Architecture

- The main application includes all features (catalogs, permissions, chat)
- The chat-only application includes only the header and chat interface
- Both applications share common UI components through the shared-components directory
- The backend detects embedded mode based on the origin/referer headers
- In embedded mode, users must have chat access permission to use the application

## API Endpoints

- `POST /api/login` - Login with username and password
- `POST /api/logout` - Logout current user
- `GET /api/check-auth` - Check if user is authenticated
- `GET /api/documents` - Get list of documents
- `GET /api/documents/<id>` - Get document by ID
