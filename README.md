# Svelte 5 + Flask App

A simple document management application with authentication, built with Svelte 5 frontend and Flask backend.

## Features

- User authentication with session management
- Document listing page
- Document detail view
- Authentication-protected routes
- Hardcoded user for testing (username: `user`, password: `user123`)

## Project Structure

```
svelte_flask/
├── backend/             # Flask backend
│   ├── app.py           # Main Flask application
│   └── requirements.txt # Python dependencies
└── frontend/            # Svelte 5 frontend
    ├── src/             # Source files
    │   ├── lib/         # Shared utilities
    │   │   └── auth.js  # Authentication logic
    │   ├── routes/      # Page components
    │   │   ├── Login.svelte
    │   │   ├── Documents.svelte
    │   │   └── DocumentDetail.svelte
    │   ├── App.svelte   # Main app component
    │   ├── main.js      # Entry point
    │   └── app.css      # Global styles
    ├── public/          # Static assets
    ├── index.html       # HTML template
    ├── package.json     # Frontend dependencies
    └── vite.config.js   # Vite configuration
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
   The backend will run at http://localhost:5000

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