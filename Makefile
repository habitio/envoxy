# Development environment setup
help:
	@echo ""
	@echo "ENVOXY DEVELOPMENT"
	@echo "=================="
	@echo ""
	@echo "Development Commands:"
	@echo "  make install-dev     Install envoxy in development mode"
	@echo "  make shell           Interactive Python shell"
	@echo ""
	@echo "Testing Commands:"
	@echo "  make test            Run all tests"
	@echo "  make test-unit       Run unit tests only"
	@echo "  make test-integration Run integration tests only"
	@echo "  make test-cov        Run tests with coverage"
	@echo "  make test-fast       Run unit tests with fail-fast"
	@echo ""
	@echo "Quality Commands:"
	@echo "  make lint            Run linting checks"
	@echo "  make format          Format code with ruff"
	@echo "  make type-check      Run type checking with mypy"
	@echo "  make quality-check   Run all quality checks"
	@echo "  make security-check  Run security checks"
	@echo ""
	@echo "Docker Commands:"
	@echo "  make docker-dev      Start development environment"
	@echo "  make docker-dev-down Stop development environment"
	@echo ""
	@echo "Note: Package building is handled by GitHub Actions"
	@echo "See .github/workflows/ for CI/CD configuration"
	@echo ""

# Development setup
install-dev:
	@echo "Installing envoxy in development mode..."
	@pip install -e .[dev,test]
	@echo "Development environment ready!"

clean:
	@echo "Cleaning build artifacts..."
	@rm -rf build/ dist/ *.egg-info vendors/dist vendors/build
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@echo "Clean complete!"

shell:
	@python scripts/prompt.py

# Test targets
test:
	@pytest -v

test-unit:
	@pytest -m unit -v

test-integration:
	@pytest -m integration -v

test-cov:
	@pytest --cov=src/envoxy --cov-report=term-missing --cov-report=html

test-fast:
	@pytest -m unit -x --tb=short

test-watch:
	@pytest-watch -- -m unit

# Docker targets
docker-dev:
	@cd docker/dev && docker compose up -d

docker-dev-down:
	@cd docker/dev && docker compose down

docker-build-runtime:
	@docker build -t envoxy:runtime -f docker/runtime/Dockerfile .

# Quality & CI targets
pre-commit-install:
	@pip install pre-commit
	@pre-commit install

pre-commit-run:
	@pre-commit run --all-files

lint:
	@ruff check src/
	@pylint src/envoxy/ --fail-under=8.0

format:
	@ruff format src/

type-check:
	@mypy src/envoxy/ --ignore-missing-imports

security-check:
	@bandit -r src/ -ll
	@safety check

deps-check:
	@pip-audit --desc

quality-check: lint type-check
	@echo "Quality checks passed!"

ci-local:
	@echo "Running CI checks locally..."
	@make lint
	@make test-unit
	@make security-check

.PHONY: help install-dev clean shell \
        test test-unit test-integration test-cov test-fast test-watch \
        docker-dev docker-dev-down docker-build-runtime \
        pre-commit-install pre-commit-run lint format type-check \
        security-check deps-check quality-check ci-local
