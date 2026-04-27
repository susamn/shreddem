# Makefile for Shreddem (Gmail Client)

.PHONY: help install build run dev clean bootstrap test check-ports docker-build docker-up docker

# Tools
PYTHON = python3
NPM = npm
VENV = .venv
BIN = $(VENV)/bin

# Auto-detect docker compose vs docker-compose
DOCKER_COMPOSE := $(shell command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1 && echo "docker compose" || echo "docker-compose")

# Default Ports
BACKEND_PORT ?= 17811
FRONTEND_PORT ?= 18710

# Default target
help:
	@echo "Shreddem Management Commands:"
	@echo "  make install    - Install backend (venv) and frontend (npm) dependencies"
	@echo "  make build      - Build frontend and copy to backend/static for production"
	@echo "  make run        - Start backend server (serves built frontend if available)"
	@echo "  make dev        - Start both backend and frontend in development mode"
	@echo "  make bootstrap  - Complete setup: install, build, and run"
	@echo "  make test       - Run backend and frontend tests"
	@echo "  make clean      - Remove build artifacts and dependencies"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-up    - Start application using $(DOCKER_COMPOSE)"
	@echo "  make docker       - Build and start application using $(DOCKER_COMPOSE)"
	@echo ""
	@echo "Port Overrides:"
	@echo "  BACKEND_PORT=8001 make run"
	@echo "  FRONTEND_PORT=3001 make dev"

check-ports:
	@if lsof -i :$(BACKEND_PORT) >/dev/null 2>&1; then \
		echo "Error: Port $(BACKEND_PORT) is already in use."; \
		echo "To use a different port, run: BACKEND_PORT=8001 make run"; \
		exit 1; \
	fi
	@if [ "$(MAKECMDGOALS)" = "dev" ] || [ "$(MAKECMDGOALS)" = "bootstrap" ]; then \
		if lsof -i :$(FRONTEND_PORT) >/dev/null 2>&1; then \
			echo "Error: Port $(FRONTEND_PORT) is already in use."; \
			echo "To use a different port, run: FRONTEND_PORT=3001 make dev"; \
			exit 1; \
		fi; \
	fi

install:
	@echo "--- Checking Dependencies ---"
	@command -v $(PYTHON) >/dev/null 2>&1 || (echo "Error: $(PYTHON) is not installed."; exit 1)
	@command -v node >/dev/null 2>&1 || (echo "Error: node is not installed."; exit 1)
	@$(PYTHON) -c "import sys; exit(0) if sys.version_info >= (3, 10) else (print('Error: Python 3.10+ required'), exit(1))"
	@node -v | grep -qE "v(1[8-9]|[2-9][0-9])" || (echo "Error: Node.js 18+ required"; exit 1)
	@echo "--- Creating Virtual Environment ---"
	test -d $(VENV) || $(PYTHON) -m venv $(VENV)
	@echo "--- Installing Backend Dependencies ---"
	$(BIN)/pip install -r backend/requirements.txt
	@echo "--- Installing Frontend Dependencies ---"
	cd frontend && $(NPM) install

build:
	@echo "--- Building Frontend ---"
	cd frontend && $(NPM) run build
	@echo "--- Deploying to Backend Static Folder ---"
	rm -rf backend/static
	cp -r frontend/dist backend/static

run: check-ports
	@echo "--- Starting Backend Server ---"
	@echo "Access the app at http://127.0.0.1:$(BACKEND_PORT)"
	cd backend && PORT=$(BACKEND_PORT) ../$(BIN)/python main.py

dev: check-ports
	@echo "--- Starting Dev Environment ---"
	@echo "Backend:  http://127.0.0.1:$(BACKEND_PORT)"
	@echo "Frontend: http://localhost:$(FRONTEND_PORT)"
	(trap 'kill 0' SIGINT; \
		(cd backend && PORT=$(BACKEND_PORT) ../$(BIN)/python main.py) & \
		(cd frontend && BACKEND_PORT=$(BACKEND_PORT) FRONTEND_PORT=$(FRONTEND_PORT) $(NPM) run dev) & \
		wait)

bootstrap: install build run

test:
	@echo "--- Running Backend Tests ---"
	cd backend && ../$(BIN)/python -m pytest
	@echo "--- Running Frontend Tests ---"
	cd frontend && $(NPM) run test

docker-build:
	@echo "--- Building Docker Image ---"
	$(DOCKER_COMPOSE) build

docker-up:
	@echo "--- Starting Docker Containers ---"
	$(DOCKER_COMPOSE) up

docker:
	@echo "--- Building and Starting Docker Containers ---"
	$(DOCKER_COMPOSE) up --build

clean:
	@echo "--- Cleaning Project ---"
	rm -rf $(VENV)
	rm -rf backend/static
	rm -rf frontend/dist
	rm -rf frontend/node_modules
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -delete
