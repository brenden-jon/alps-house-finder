PY := scrapers/.venv/bin/python
ALPS := scrapers/.venv/bin/alpsfinder

.PHONY: setup init-db load-communes scrape score rank export refresh dashboard-dev

setup:
	cd scrapers && uv venv --python 3.12 && uv pip install -e ".[dev]" --python .venv/bin/python

init-db:
	$(ALPS) init-db

load-communes:
	$(ALPS) load-communes

scrape:
	$(ALPS) scrape

score:
	$(ALPS) score

rank:
	$(ALPS) rank --top 20

export:
	$(ALPS) export

refresh:
	$(ALPS) refresh

dashboard-dev:
	cd web && npm run dev

test:
	cd scrapers && .venv/bin/pytest
