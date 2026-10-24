# Órdenes habituales. Ver docs/desarrollo.md.
PY ?= .venv/bin/python
PRODUCCION = https://photo-recommender.vercel.app

.PHONY: instalar check check-python check-web formato test web e2e e2e-produccion datos prevision

instalar:
	python3 -m venv .venv
	$(PY) -m pip install -e ".[dev]"
	npm ci

check: check-python check-web

check-python:
	$(PY) -m ruff check .
	$(PY) -m ruff format --check .
	$(PY) -m pytest -q

check-web:
	npm run check

formato:
	$(PY) -m ruff format .
	$(PY) -m ruff check --fix .
	npm run format

test:
	$(PY) -m pytest -q

web:
	npm run build
	npm start

e2e:
	npx playwright test

e2e-produccion:
	BASE_URL=$(PRODUCCION) npx playwright test

datos:
	npm run datos

prevision:
	$(PY) -m rasante prevision --mis-spots mis_spots.csv
