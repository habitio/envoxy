help:
	./.build help

clean:
	./.build clean

envoxyd:
	./.build envoxyd

envoxyd_install:
	./.build envoxyd_install

envoxy_install:
	./.build envoxy_install

install:
	./.build install

prompt:
	python scripts/prompt.py

shell:
	python scripts/prompt.py

packages:
	./.build packages
