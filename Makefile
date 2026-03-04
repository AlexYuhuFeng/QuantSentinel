.PHONY: lint test i18n-check i18n-build

POETRY ?= poetry
PO_FILE ?= locales/zh_CN/LC_MESSAGES/quantsentinel.po

lint:
	$(POETRY) run ruff check .

test:
	$(POETRY) run pytest --cov=src/quantsentinel --cov-report=term-missing

i18n-check:
	$(POETRY) run python scripts/check_missing_translations.py locales/en/LC_MESSAGES/quantsentinel.po
	$(POETRY) run python scripts/check_missing_translations.py locales/zh_CN/LC_MESSAGES/quantsentinel.po
	$(POETRY) run python scripts/check_streamlit_i18n.py
	$(POETRY) run python scripts/i18n_build.py --check

i18n-build:
	$(POETRY) run python scripts/i18n_build.py

coverage-domain-services:
	$(POETRY) run pytest --cov=src/quantsentinel --cov-report=json --cov-report=term-missing --cov-fail-under=0 --cov-fail-under=0
	$(POETRY) run python scripts/check_domain_services_coverage.py --report coverage.json --min 90

ci:
	$(POETRY) run ruff check $(RUFF_SCOPE)
	$(POETRY) run pytest --cov=src/quantsentinel --cov-report=json --cov-report=term-missing --cov-fail-under=0 --cov-fail-under=0
	$(POETRY) run python scripts/check_domain_services_coverage.py --report coverage.json --min 90

acceptance:
	bash scripts/acceptance_oneclick.sh
