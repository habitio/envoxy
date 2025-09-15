PYTHONPATH := src:.
SERVICE_MODELS := examples.template_service.models
ALEMBIC_DIR ?= alembic
ENVOXY_ALEMBIC_DEBUG ?= 1
# Mandatory service namespace; env.py derives prefix aux_<ns>_
ENVOXY_SERVICE_NAMESPACE ?= examples_template_service
ALEMBIC := envoxy-alembic
AL := SERVICE_MODELS=$(SERVICE_MODELS) SERVICE_ALEMBIC_DIR=$(ALEMBIC_DIR) \
	$(if $(ENVOXY_ALEMBIC_DEBUG),ENVOXY_ALEMBIC_DEBUG=$(ENVOXY_ALEMBIC_DEBUG) ,) \
	ENVOXY_SERVICE_NAMESPACE=$(ENVOXY_SERVICE_NAMESPACE) \
	$(ALEMBIC)

.PHONY: require-namespace alembic-rev alembic-upgrade alembic-downgrade alembic-current alembic-history alembic-heads alembic-stamp alembic-show alembic-merge alembic-help alembic generic-alembic

require-namespace:
	@test -n "$(ENVOXY_SERVICE_NAMESPACE)" || (echo 'ENVOXY_SERVICE_NAMESPACE is required (used to derive aux_<ns>_ prefix and version table)'; exit 2)

# Create a new revision (message required: m="message"). Add AUTO=1 to autogenerate.
alembic-rev: require-namespace
	@test -n "$(m)" || (echo 'Usage: make alembic-rev m="message" [AUTO=1]'; exit 2)
	$(AL) revision -m "$(m)" $(if $(AUTO),--autogenerate,)

# Upgrade to head or specify rev=xxxx
alembic-upgrade: require-namespace
	$(AL) upgrade $(if $(rev),$(rev),head)

# Downgrade one or more steps: e.g. make alembic-downgrade rev=-1
alembic-downgrade: require-namespace
	@test -n "$(rev)" || (echo 'Usage: make alembic-downgrade rev="-1"|"base"|"<revision>"'; exit 2)
	$(AL) downgrade $(rev)

alembic-current: require-namespace
	$(AL) current

alembic-history: require-namespace
	$(AL) history $(if $(verbose),--verbose,)

alembic-heads: require-namespace
	$(AL) heads

# Stamp the database with a given revision (no migration run). Usage: make alembic-stamp rev=head
alembic-stamp: require-namespace
	@test -n "$(rev)" || (echo 'Usage: make alembic-stamp rev="head"|"<revision>"'; exit 2)
	$(AL) stamp $(rev)

# Show a particular revision: make alembic-show rev=<revision>
alembic-show: require-namespace
	@test -n "$(rev)" || (echo 'Usage: make alembic-show rev="<revision>"'; exit 2)
	$(AL) show $(rev)

# Merge two heads: make alembic-merge revs="rev1 rev2" m="merge heads"
alembic-merge: require-namespace
	@test -n "$(revs)" || (echo 'Usage: make alembic-merge revs="rev1 rev2" m="message"'; exit 2)
	@test -n "$(m)" || (echo 'Merge requires m="message"'; exit 2)
	$(AL) merge -m "$(m)" $(revs)

# Generic pass-through: make alembic cmd="upgrade head" or cmd="history --verbose"
alembic: require-namespace
	@test -n "$(cmd)" || (echo 'Usage: make alembic cmd="<alembic subcommand args>"'; exit 2)
	$(AL) $(cmd)

alembic-help:
	@echo "Alembic targets:"; \
	echo "  make alembic-rev m=msg [AUTO=1]"; \
	echo "  make alembic-upgrade [rev=head]"; \
	echo "  make alembic-downgrade rev=-1"; \
	echo "  make alembic-current"; \
	echo "  make alembic-history [verbose=1]"; \
	echo "  make alembic-heads"; \
	echo "  make alembic-stamp rev=head"; \
	echo "  make alembic-show rev=<rev>"; \
	echo "  make alembic-merge revs=rev1\\ rev2 m=msg"; \
	echo "  make alembic cmd=\"upgrade head\" (generic passthrough)"; \
	echo "Variables:"; \
	echo "  SERVICE_MODELS=$(SERVICE_MODELS)"; \
	echo "  ALEMBIC_DIR=$(ALEMBIC_DIR)"; \
	echo "  ENVOXY_ALEMBIC_DEBUG=$(ENVOXY_ALEMBIC_DEBUG)"; \
	echo "  ENVOXY_SERVICE_NAMESPACE=$(ENVOXY_SERVICE_NAMESPACE)"; \
	echo "Examples:"; \
	echo "  make alembic-upgrade ENVOXY_SERVICE_NAMESPACE=ordersvc ENVOXY_ALEMBIC_DEBUG=1"; \
	echo "  make alembic-upgrade ENVOXY_ALEMBIC_DEBUG=1 (show managed tables for this namespace)";

