.PHONY: setup-backend setup-frontend setup build-backend build-frontend build run static clean serve-static kill-ports

# Setup both backend and frontend
setup: setup-backend setup-frontend

# Setup backend
setup-backend:
	cd backend && pip install -r requirements.txt

# Setup frontend
setup-frontend:
	cd frontend && npm install

# Build both backend and frontend
build: build-backend build-frontend

# Build backend (no specific build step for Flask, just a placeholder)
build-backend:
	@echo "Flask backend doesn't require a build step"

# Build frontend for development
build-frontend:
	cd frontend && npm run build

# Run both applications together
run: 
	@echo "Starting Flask backend and Svelte frontend..."
	@trap 'kill 0' SIGINT SIGTERM EXIT; \
	(cd backend && python app.py) & \
	(cd frontend && npm run dev) & \
	wait

# Build frontend as a static site
static:
	@echo "Building Svelte app as a static site..."
	cd frontend && npm run build
	@echo "Static site built in frontend/dist/"

# Serve the static site with Flask
serve-static: kill-ports static
	@echo "Creating Flask static server..."
	@mkdir -p backend/static
	@rm -rf backend/static/* # Clear previous static files
	@cp -r frontend/dist/* backend/static/
	@echo "Setting correct permissions..."
	@chmod -R 755 backend/static
	@echo "Serving static site with Flask..."
	@trap 'kill 0' SIGINT SIGTERM EXIT; \
	cd backend && STATIC_MODE=true python app.py

# Clean build artifacts
clean:
	rm -rf frontend/dist
	rm -rf frontend/node_modules
	rm -rf backend/static
	find . -name __pycache__ -type d -exec rm -rf {} +
	find . -name "*.pyc" -delete
	
# Kill processes using specific ports (8000 for Flask, 5173 for Vite)
kill-ports:
	@echo "Killing processes on ports 8000 and 5173..."
	-@lsof -ti:8000 | xargs kill -9 2>/dev/null || true
	-@lsof -ti:5173 | xargs kill -9 2>/dev/null || true
	@echo "Ports cleared."
