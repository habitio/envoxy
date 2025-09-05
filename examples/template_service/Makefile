PYTHONPATH := src:.
SERVICE_MODELS := examples.template_service.models
ALEMBIC_DIR ?= alembic
ALEMBIC := envoxy-alembic
AL := SERVICE_MODELS=$(SERVICE_MODELS) SERVICE_ALEMBIC_DIR=$(ALEMBIC_DIR) $(ALEMBIC)

.PHONY: alembic-rev alembic-upgrade alembic-downgrade alembic-current alembic-history alembic-heads alembic-stamp alembic-show alembic-merge alembic-help alembic generic-alembic

# Create a new revision (message required: m="message"). Add AUTO=1 to autogenerate.
alembic-rev:
	@test -n "$(m)" || (echo 'Usage: make alembic-rev m="message" [AUTO=1]'; exit 2)
	$(AL) revision -m "$(m)" $(if $(AUTO),--autogenerate,)

# Upgrade to head or specify rev=xxxx
alembic-upgrade:
	$(AL) upgrade $(if $(rev),$(rev),head)

# Downgrade one or more steps: e.g. make alembic-downgrade rev=-1
alembic-downgrade:
	@test -n "$(rev)" || (echo 'Usage: make alembic-downgrade rev="-1"|"base"|"<revision>"'; exit 2)
	$(AL) downgrade $(rev)

alembic-current:
	$(AL) current

alembic-history:
	$(AL) history $(if $(verbose),--verbose,)

alembic-heads:
	$(AL) heads

# Stamp the database with a given revision (no migration run). Usage: make alembic-stamp rev=head
alembic-stamp:
	@test -n "$(rev)" || (echo 'Usage: make alembic-stamp rev="head"|"<revision>"'; exit 2)
	$(AL) stamp $(rev)

# Show a particular revision: make alembic-show rev=<revision>
alembic-show:
	@test -n "$(rev)" || (echo 'Usage: make alembic-show rev="<revision>"'; exit 2)
	$(AL) show $(rev)

# Merge two heads: make alembic-merge revs="rev1 rev2" m="merge heads"
alembic-merge:
	@test -n "$(revs)" || (echo 'Usage: make alembic-merge revs="rev1 rev2" m="message"'; exit 2)
	@test -n "$(m)" || (echo 'Merge requires m="message"'; exit 2)
	$(AL) merge -m "$(m)" $(revs)

# Generic pass-through: make alembic cmd="upgrade head" or cmd="history --verbose"
alembic:
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
	echo "Variables: SERVICE_MODELS=$(SERVICE_MODELS) ALEMBIC_DIR=$(ALEMBIC_DIR)";

