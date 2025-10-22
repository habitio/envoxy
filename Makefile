help:
	@./tools/build.sh help

clean:
	@./tools/build.sh clean

envoxyd:
	@./tools/build.sh envoxyd

install:
	@./tools/build.sh install

develop:
	@./tools/build.sh develop

packages:
	@./tools/build.sh packages

info:
	@./tools/build.sh info

prompt:
	python scripts/prompt.py

shell:
	python scripts/prompt.py

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
	cd docker/dev && docker-compose up -d

docker-dev-down:
	cd docker/dev && docker-compose down

docker-build-runtime:
	docker build -t envoxy:runtime -f docker/runtime/Dockerfile .

docker-build-builder:
	docker build --build-arg UID=$$(id -u) --build-arg GID=$$(id -g) \
		-t envoxy-ubuntu:24.04 -f docker/builder/ubuntu-24.04.Dockerfile .

# CI/CD targets
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

.PHONY: help clean envoxyd install develop packages info prompt shell \
        test test-unit test-integration test-cov test-fast test-watch \
        docker-dev docker-dev-down docker-build-runtime docker-build-builder \
        pre-commit-install pre-commit-run lint format type-check \
        security-check deps-check quality-check ci-local
