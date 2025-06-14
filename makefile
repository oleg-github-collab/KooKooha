# Human Lens API Makefile
.PHONY: help install dev run test lint format clean migrate logs deploy health

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python3.12
PIP := pip
VENV := venv
PORT := 8000
HOST := 0.0.0.0

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)Human Lens API - Available Commands$(NC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "$(GREEN)%-15s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies and setup virtual environment
	@echo "$(YELLOW)Setting up virtual environment...$(NC)"
	$(PYTHON) -m venv $(VENV)
	@echo "$(YELLOW)Installing dependencies...$(NC)"
	$(VENV)/bin/$(PIP) install --upgrade pip
	$(VENV)/bin/$(PIP) install -r requirements.txt
	@echo "$(GREEN)Installation completed!$(NC)"
	@echo "$(BLUE)To activate virtual environment: source $(VENV)/bin/activate$(NC)"

dev-install: install ## Install development dependencies
	@echo "$(YELLOW)Installing development dependencies...$(NC)"
	$(VENV)/bin/$(PIP) install pytest pytest-asyncio pytest-cov black isort ruff pre-commit
	$(VENV)/bin/pre-commit install
	@echo "$(GREEN)Development setup completed!$(NC)"

run: ## Run the development server
	@echo "$(YELLOW)Starting Human Lens API server...$(NC)"
	$(VENV)/bin/python -m uvicorn app.main:app --host $(HOST) --port $(PORT) --reload

prod-run: ## Run the production server
	@echo "$(YELLOW)Starting Human Lens API in production mode...$(NC)"
	$(VENV)/bin/python -m uvicorn app.main:app --host $(HOST) --port $(PORT) --workers 4

test: ## Run tests
	@echo "$(YELLOW)Running tests...$(NC)"
	$(VENV)/bin/python -m pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing

test-quick: ## Run tests without coverage
	@echo "$(YELLOW)Running quick tests...$(NC)"
	$(VENV)/bin/python -m pytest tests/ -v -x

lint: ## Run linting
	@echo "$(YELLOW)Running linters...$(NC)"
	$(VENV)/bin/ruff check app/ tests/
	$(VENV)/bin/black --check app/ tests/
	$(VENV)/bin/isort --check-only app/ tests/

format: ## Format code
	@echo "$(YELLOW)Formatting code...$(NC)"
	$(VENV)/bin/black app/ tests/
	$(VENV)/bin/isort app/ tests/
	$(VENV)/bin/ruff check --fix app/ tests/
	@echo "$(GREEN)Code formatted!$(NC)"

type-check: ## Run type checking
	@echo "$(YELLOW)Running type checks...$(NC)"
	$(VENV)/bin/python -m mypy app/ --ignore-missing-imports

migrate: ## Run database migrations
	@echo "$(YELLOW)Running database migrations...$(NC)"
	$(VENV)/bin/python -c "from app.database import create_db_and_tables; create_db_and_tables()"
	@echo "$(GREEN)Database migrations completed!$(NC)"

seed-data: ## Seed database with sample data
	@echo "$(YELLOW)Seeding database with sample data...$(NC)"
	$(VENV)/bin/python -m app.scripts.seed_data
	@echo "$(GREEN)Database seeded!$(NC)"

clean: ## Clean up temporary files and cache
	@echo "$(YELLOW)Cleaning up...$(NC)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf dist/
	rm -rf build/
	@echo "$(GREEN)Cleanup completed!$(NC)"

logs: ## View application logs
	@echo "$(YELLOW)Viewing logs...$(NC)"
	tail -f logs/app.log

logs-error: ## View error logs only
	@echo "$(YELLOW)Viewing error logs...$(NC)"
	tail -f logs/app.log | grep ERROR

health: ## Check application health
	@echo "$(YELLOW)Checking application health...$(NC)"
	@curl -s http://localhost:$(PORT)/health | python -m json.tool || echo "$(RED)Application not responding$(NC)"

api-docs: ## Open API documentation
	@echo "$(YELLOW)Opening API documentation...$(NC)"
	@echo "$(BLUE)API Docs: http://localhost:$(PORT)/docs$(NC)"
	@echo "$(BLUE)ReDoc: http://localhost:$(PORT)/redoc$(NC)"

backup-db: ## Backup database
	@echo "$(YELLOW)Creating database backup...$(NC)"
	@mkdir -p backups
	@cp data/human_lens.db backups/human_lens_$(shell date +%Y%m%d_%H%M%S).db
	@echo "$(GREEN)Database backup created!$(NC)"

restore-db: ## Restore database from backup (usage: make restore-db BACKUP=filename)
	@echo "$(YELLOW)Restoring database from backup...$(NC)"
	@if [ -z "$(BACKUP)" ]; then \
		echo "$(RED)Please specify backup file: make restore-db BACKUP=filename$(NC)"; \
		exit 1; \
	fi
	@cp backups/$(BACKUP) data/human_lens.db
	@echo "$(GREEN)Database restored from $(BACKUP)!$(NC)"

security-check: ## Run security checks
	@echo "$(YELLOW)Running security checks...$(NC)"
	$(VENV)/bin/pip install safety bandit
	$(VENV)/bin/safety check
	$(VENV)/bin/bandit -r app/ -f json -o security-report.json || true
	@echo "$(GREEN)Security check completed! Report saved to security-report.json$(NC)"

docker-build: ## Build Docker image (if needed in future)
	@echo "$(YELLOW)Building Docker image...$(NC)"
	docker build -t human-lens-api .
	@echo "$(GREEN)Docker image built!$(NC)"

env-check: ## Check environment configuration
	@echo "$(YELLOW)Checking environment configuration...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(RED).env file not found! Copy .env.example to .env and configure it.$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)Environment configuration found!$(NC)"

deps-check: ## Check for outdated dependencies
	@echo "$(YELLOW)Checking for outdated dependencies...$(NC)"
	$(VENV)/bin/pip list --outdated

deps-update: ## Update dependencies (be careful in production)
	@echo "$(YELLOW)Updating dependencies...$(NC)"
	$(VENV)/bin/pip install --upgrade -r requirements.txt
	@echo "$(GREEN)Dependencies updated!$(NC)"

generate-secret: ## Generate a new secret key
	@echo "$(YELLOW)Generating new secret key...$(NC)"
	@python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"

setup-production: ## Setup for production environment
	@echo "$(YELLOW)Setting up production environment...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(RED)Please create .env file first!$(NC)"; \
		exit 1; \
	fi
	make install
	make migrate
	@echo "$(GREEN)Production setup completed!$(NC)"

systemd-install: ## Install systemd service (on Ubuntu/Debian)
	@echo "$(YELLOW)Installing systemd service...$(NC)"
	sudo cp deploy/human-lens-api.service /etc/systemd/system/
	sudo systemctl daemon-reload
	sudo systemctl enable human-lens-api
	@echo "$(GREEN)Systemd service installed!$(NC)"
	@echo "$(BLUE)Start with: sudo systemctl start human-lens-api$(NC)"

systemd-status: ## Check systemd service status
	@echo "$(YELLOW)Checking service status...$(NC)"
	sudo systemctl status human-lens-api

systemd-logs: ## View systemd service logs
	@echo "$(YELLOW)Viewing service logs...$(NC)"
	sudo journalctl -u human-lens-api -f

deploy: ## Deploy to production (DigitalOcean)
	@echo "$(YELLOW)Deploying to production...$(NC)"
	@if [ ! -f deploy.sh ]; then \
		echo "$(RED)deploy.sh not found!$(NC)"; \
		exit 1; \
	fi
	chmod +x deploy.sh
	./deploy.sh
	@echo "$(GREEN)Deployment completed!$(NC)"

quick-start: ## Quick start for new developers
	@echo "$(BLUE)Human Lens API Quick Start$(NC)"
	@echo "$(YELLOW)1. Creating environment and installing dependencies...$(NC)"
	make dev-install
	@echo "$(YELLOW)2. Setting up environment file...$(NC)"
	@if [ ! -f .env ]; then cp .env.example .env; fi
	@echo "$(YELLOW)3. Running database migrations...$(NC)"
	make migrate
	@echo "$(YELLOW)4. Running tests...$(NC)"
	make test-quick
	@echo "$(GREEN)Quick start completed!$(NC)"
	@echo "$(BLUE)Run 'make run' to start the development server$(NC)"

ci-test: ## Run tests in CI environment
	@echo "$(YELLOW)Running CI tests...$(NC)"
	$(VENV)/bin/python -m pytest tests/ -v --cov=app --cov-report=xml

performance-test: ## Run performance tests
	@echo "$(YELLOW)Running performance tests...$(NC)"
	@echo "$(RED)Performance tests not yet implemented$(NC)"
	# Could add locust or similar tool here

stress-test: ## Run stress tests
	@echo "$(YELLOW)Running stress tests...$(NC)"
	@command -v ab >/dev/null 2>&1 || { echo "$(RED)Apache Bench (ab) not installed$(NC)"; exit 1; }
	ab -n 1000 -c 10 http://localhost:$(PORT)/health

load-test: ## Run load tests
	@echo "$(YELLOW)Running load tests...$(NC)"
	@command -v wrk >/dev/null 2>&1 || { echo "$(RED)wrk not installed$(NC)"; exit 1; }
	wrk -t4 -c100 -d30s http://localhost:$(PORT)/health

init-project: ## Initialize new project (for first-time setup)
	@echo "$(BLUE)Initializing Human Lens API project...$(NC)"
	@mkdir -p data logs backups static frontend
	@mkdir -p tests/unit tests/integration tests/e2e
	@touch logs/app.log
	@echo "$(GREEN)Project structure initialized!$(NC)"

show-urls: ## Show all application URLs
	@echo "$(BLUE)Human Lens API URLs:$(NC)"
	@echo "$(GREEN)Health Check:$(NC) http://localhost:$(PORT)/health"
	@echo "$(GREEN)API Docs:$(NC) http://localhost:$(PORT)/docs"
	@echo "$(GREEN)ReDoc:$(NC) http://localhost:$(PORT)/redoc"
	@echo "$(GREEN)API Root:$(NC) http://localhost:$(PORT)/"

# Development workflow shortcuts
dev: clean install migrate run ## Full development setup and run

prod: clean setup-production prod-run ## Full production setup and run

full-test: lint type-check test ## Run all tests and checks

# Emergency commands
emergency-stop: ## Emergency stop all processes
	@echo "$(RED)Emergency stop - killing all Python processes...$(NC)"
	@pkill -f "uvicorn app.main:app" || true
	@echo "$(YELLOW)Processes stopped$(NC)"

emergency-backup: ## Emergency database backup
	@echo "$(RED)Creating emergency backup...$(NC)"
	@mkdir -p emergency-backups
	@cp data/human_lens.db emergency-backups/emergency_$(shell date +%Y%m%d_%H%M%S).db
	@echo "$(GREEN)Emergency backup created!$(NC)"