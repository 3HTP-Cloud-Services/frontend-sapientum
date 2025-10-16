# Sapientum Frontend Application

This is a frontend-only application that consists of two separate Svelte frontends sharing common components:

1. **Main Frontend** - Full application with all features
2. **Chat Frontend** - Streamlined interface with only chat functionality

Both frontends are designed to connect to an external backend API.
 
## Project Structure

```
/
  /frontend/                 # Main Svelte application
  /chat-frontend/            # Chat-only Svelte application  
  /shared-components/        # Shared UI components and utilities
  backend-config.json        # Backend API configuration
  build.sh                   # Build script for production
```

## Production Build (Terraform Cloud)

For production deployment via Terraform Cloud, simply run:

```bash
./build.sh
```

This script will:
- Install Node.js 18 if needed (on Linux)
- Install all dependencies
- Build both frontend applications
- Create optimized production builds in `dist/`

### Build Output

```
dist/
├── main/              # Main application build
├── chat/              # Chat application build
└── build-info.json    # Build metadata
```

## Backend Configuration

Edit `backend-config.json` to configure your backend API:

```json
{
  "apiUrl": "https://your-backend-api.com"
}
```

## Local Development

For local development:

```bash
# Main frontend
cd frontend
npm install
npm run dev  # Runs on http://localhost:5173

# Chat frontend
cd chat-frontend
npm install
npm run dev  # Runs on http://localhost:5573
```

## API Integration

The frontend expects these backend endpoints:

- `POST /api/login` - User authentication
- `POST /api/logout` - User logout
- `GET /api/check-auth` - Authentication check
- `GET /api/documents` - Document listing
- `GET /api/documents/<id>` - Document details
