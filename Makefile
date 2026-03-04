.PHONY: lint test i18n-check i18n-build ci coverage-domain-services acceptance

PO_FILE ?= locales/zh_CN/LC_MESSAGES/quantsentinel.po

lint:
	ruff check .

test:
	PYTHONPATH=src pytest -q --cov=src/quantsentinel --cov-report=term-missing

i18n-check:
	python scripts/check_missing_translations.py $(PO_FILE)
	python scripts/check_streamlit_i18n.py

i18n-build:
	pybabel compile -d locales -D quantsentinel

coverage-domain-services:
	PYTHONPATH=src pytest -q --cov=src/quantsentinel --cov-report=json --cov-report=term-missing
	python scripts/check_domain_services_coverage.py --report coverage.json --min 90

ci:
	$(MAKE) lint
	$(MAKE) test
	$(MAKE) i18n-check

acceptance:
	bash scripts/acceptance_oneclick.sh
