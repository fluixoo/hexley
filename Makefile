.PHONY: install test lint doctor watch launches dashboard

install:
	pip install -e ".[dev]"

test:
	pytest

lint:
	ruff check chaindesk tests

doctor:
	python -m chaindesk doctor

watch:
	python -m chaindesk watch --config desk.toml

launches:
	python -m chaindesk launches --last 2000

dashboard:
	python -m http.server 8787 --directory dashboard
