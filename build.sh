#!/bin/bash

set -e  # Exit on any error

echo "🚀 Starting Sapientum Frontend Build Process..."

# Function to check and install Node.js if needed
setup_nodejs() {
    if ! command -v node &> /dev/null; then
        echo "📦 Installing Node.js 18..."
        # Usar instalación manual para evitar conflictos con dnf
        curl -fsSL https://nodejs.org/dist/v18.19.0/node-v18.19.0-linux-x64.tar.xz -o node.tar.xz
        tar -xf node.tar.xz
        cp -r node-v18.19.0-linux-x64/* /usr/local/
        rm -rf node.tar.xz node-v18.19.0-linux-x64
        
        # Crear enlaces simbólicos
        ln -sf /usr/local/bin/node /usr/bin/node
        ln -sf /usr/local/bin/npm /usr/bin/npm
    fi

    NODE_VERSION=$(node -v)
    echo "✅ Using Node.js version: $NODE_VERSION"
}

# Function to build a frontend application
build_frontend() {
    local app_dir=$1
    local app_name=$2

    echo "🔨 Building $app_name..."
    cd "$app_dir"

    # Clean previous builds
    rm -rf node_modules package-lock.json dist

    # Install dependencies
    echo "📦 Installing dependencies for $app_name..."
    npm install --legacy-peer-deps --silent --no-audit --no-fund

    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies for $app_name"
        exit 1
    fi

    # Build the application
    echo "⚡ Compiling $app_name..."
    npm run build

    if [ $? -ne 0 ]; then
        echo "❌ Failed to build $app_name"
        exit 1
    fi

    echo "✅ $app_name built successfully"
    cd ..
}

# Main build process
main() {
    echo "🏗️  Starting build process..."

    # Setup Node.js
    setup_nodejs

    # Create build output directory
    mkdir -p dist
    rm -rf dist/*

    # Install shared-components dependencies first
    echo "📦 Installing shared-components dependencies..."
    cd shared-components
    npm install --legacy-peer-deps --silent --no-audit --no-fund
    cd ..

    # Build main frontend
    build_frontend "frontend" "Main Frontend"

    # Copy main frontend build
    cp -r frontend/dist dist/main

    # Build chat frontend
    build_frontend "chat-frontend" "Chat Frontend"

    # Copy chat frontend build
    cp -r chat-frontend/dist dist/chat

    # Create build info
    cat > dist/build-info.json << EOF
{
  "buildTime": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "buildHost": "$(hostname)",
  "nodeVersion": "$(node -v)",
  "npmVersion": "$(npm -v)",
  "applications": {
    "main": {
      "path": "main/",
      "description": "Full Sapientum application with all features"
    },
    "chat": {
      "path": "chat/",
      "description": "Chat-only Sapientum application"
    }
  }
}
EOF

    echo ""
    echo "🎉 Build completed successfully!"
    echo "📁 Build output structure:"
    echo "   dist/"
    echo "   ├── main/          # Main application"
    echo "   ├── chat/          # Chat-only application"
    echo "   └── build-info.json"
    echo ""
    echo "📊 Build statistics:"
    echo "   Main app files: $(find dist/main -type f | wc -l)"
    echo "   Chat app files: $(find dist/chat -type f | wc -l)"
    echo "   Total size: $(du -sh dist | cut -f1)"
    echo ""
    echo "✅ Ready for Terraform deployment to S3!"
}

# Run main function
main "$@"
