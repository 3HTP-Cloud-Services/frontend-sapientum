# Chat-Only Embedded Frontend

This is a stripped-down version of the main application that only includes the chat functionality. It's designed to be run on a separate port (5573) while communicating with the same backend.

## Features

- Login page
- Chat-only interface
- Uses the same backend as the main application
- Simplified UI without catalog listing or permissions UI

## Getting Started

1. Make sure the backend is running on port 8000:
   ```
   cd ../backend
   python app.py
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Run the development server:
   ```
   npm run dev
   ```

4. The application will be available at:
   ```
   http://localhost:5573
   ```

## How It Works

This frontend is configured to:
1. Always run in "embedded mode"
2. Connect to the main backend at http://localhost:8000
3. Only display the chat interface, removing catalog and permissions management
4. Enforce chat access permissions for users

## Login Credentials

Use the same credentials as the main application to log in.

## Note

This is a specialized version of the frontend designed specifically for embedding the chat functionality on external websites.