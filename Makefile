.PHONY: lint test i18n-check i18n-build

POETRY ?= poetry
PO_FILE ?= locales/zh_CN/LC_MESSAGES/quantsentinel.po

lint:
	$(POETRY) run ruff check .

test:
	$(POETRY) run pytest --cov=src/quantsentinel --cov-report=term-missing

i18n-check:
	$(POETRY) run python scripts/check_missing_translations.py $(PO_FILE)
	$(POETRY) run python scripts/check_streamlit_i18n.py

i18n-build:
	$(POETRY) run pybabel compile -d locales -D quantsentinel
