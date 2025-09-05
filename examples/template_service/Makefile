PYTHONPATH := src:.
SERVICE_MODELS := examples.template_service.models

.PHONY: alembic-rev alembic-upgrade alembic-current

alembic-rev:
	SERVICE_MODELS=$(SERVICE_MODELS) envoxy-alembic revision -m "$(m)" --autogenerate

alembic-upgrade:
	SERVICE_MODELS=$(SERVICE_MODELS) envoxy-alembic upgrade head

alembic-current:
	SERVICE_MODELS=$(SERVICE_MODELS) envoxy-alembic current
