PYTHONPATH := src:.
SERVICE_MODELS := examples.template_service.models

.PHONY: alembic-rev alembic-upgrade alembic-current

alembic-rev:
	PYTHONPATH=$(PYTHONPATH) SERVICE_MODELS=$(SERVICE_MODELS) ./scripts/alembic.sh revision -m "$(m)"

alembic-upgrade:
	PYTHONPATH=$(PYTHONPATH) SERVICE_MODELS=$(SERVICE_MODELS) ./scripts/alembic.sh upgrade head

alembic-current:
	PYTHONPATH=$(PYTHONPATH) SERVICE_MODELS=$(SERVICE_MODELS) ./scripts/alembic.sh current
