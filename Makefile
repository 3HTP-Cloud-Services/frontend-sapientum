.PHONY: setup-backend setup-frontend setup build-backend build-frontend build run static clean serve-static kill-ports init-frontend test-backend

# Setup both backend and frontend
setup: setup-backend setup-frontend

# Setup backend
setup-backend:
	cd backend && pip install -r requirements.txt

# Setup frontend
setup-frontend:
	cd merged_frontend && npm install

# Build both backend and frontend
build: build-backend build-frontend

# Build backend (no specific build step for Flask, just a placeholder)
build-backend:
	@echo "Flask backend doesn't require a build step"

# Build frontend for development
build-frontend:
	@echo "Building merged frontend..."
	cd merged_frontend && npm run build:both

# Run both applications together
run: 
	@echo "Starting Flask backend and merged frontend..."
	@trap 'kill 0' SIGINT SIGTERM EXIT; \
	(cd backend && export FLASK_ENV=development; python app.py) & \
	(cd merged_frontend && npm run dev:both) & \
	wait

# Build frontend as a static site
static:
	@echo "Cleaning static directories..."
	@rm -rf backend/static
	@rm -rf merged_frontend/frontend/dist
	@rm -rf merged_frontend/embed-frontend/dist
	@echo "Building merged frontend as static sites..."
	cd merged_frontend && npm run build:both
	@mkdir -p backend/static
	@cp -r merged_frontend/frontend/dist/* backend/static/
	@mkdir -p backend/static/embed
	@cp -r merged_frontend/embed-frontend/dist/* backend/static/embed/
	@echo "Static sites built and copied to backend/static/" 

# Serve the static site with Flask
serve-static: kill-ports static
	@echo "Creating Flask static server..."
	@echo "Setting correct permissions..."
	@chmod -R 755 backend/static
	@echo "Serving static sites with Flask..."
	@trap 'kill 0' SIGINT SIGTERM EXIT; \
	cd backend && STATIC_MODE=true python app.py

# Clean build artifacts
clean:
	rm -rf merged_frontend/frontend/dist
	rm -rf merged_frontend/embed-frontend/dist
	rm -rf merged_frontend/node_modules
	rm -rf backend/static
	find . -name __pycache__ -type d -exec rm -rf {} +
	find . -name "*.pyc" -delete
	
# Kill processes using specific ports (8000 for Flask, 5173 and 5573 for Vite)
kill-ports:
	@echo "Killing processes on ports 8000, 5173, and 5573..."
	-@lsof -ti:8000 | xargs kill -9 2>/dev/null || true
	-@lsof -ti:5173 | xargs kill -9 2>/dev/null || true
	-@lsof -ti:5573 | xargs kill -9 2>/dev/null || true
	@echo "Ports cleared."

# Check Python files for syntax correctness (excluding .venv directory)
lint-backend:
	@echo "Checking Python files for syntax correctness..."
	@cd backend && python -m pip install autopep8 && python -m autopep8 --in-place --recursive --max-line-length=100 --select=W291,W293,E501 --exclude ".venv" .
	@find backend -name "*.py" -type f -not -path "*/\.venv/*" -exec echo "Checking {}" \; -exec python -m py_compile {} \;
	@find backend -name "*.py" -type f -not -path "*/\.venv/*" -exec echo "Checking {}" \; -exec pylint {} \;
	@echo "Syntax check completed."

# Initialize frontend projects with npm install
init-frontend:
	@echo "Installing dependencies for merged frontend project..."
	cd merged_frontend && npm install
	@echo "Dependencies installed successfully."

# Run backend unit tests
test-backend:
	@echo "Running backend unit tests..."
	cd backend && python -m unittest discover -s . -p "test_*.py" -v
	@echo "Unit tests completed."
