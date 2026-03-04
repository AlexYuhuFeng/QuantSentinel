.PHONY: lint test i18n-check i18n-build ci coverage-domain-services acceptance

POETRY ?= poetry
PO_FILE ?= locales/zh_CN/LC_MESSAGES/quantsentinel.po

RUFF_SCOPE = \
	src/quantsentinel/domain/market/indicators.py \
	src/quantsentinel/domain/alerts/rules.py \
	src/quantsentinel/domain/research/walk_forward.py \
	src/quantsentinel/domain/research/metrics.py \
	tests/unit/domain/test_indicators_and_rules.py \
	tests/unit/domain/test_research_metrics_walk_forward.py \
	tests/unit/domain/test_alert_expression_security.py \
	tests/integration/db/test_migrations_contract.py \
	tests/integration/tasks/test_task_enqueue_integration.py \
	tests/integration/test_rbac_gating.py \
	scripts/check_domain_services_coverage.py

lint:
	$(POETRY) run ruff check $(RUFF_SCOPE)

test:
	$(POETRY) run pytest --cov=src/quantsentinel --cov-report=term-missing --cov-fail-under=0

i18n-check:
	$(POETRY) run python scripts/check_missing_translations.py $(PO_FILE)
	$(POETRY) run python scripts/check_streamlit_i18n.py

i18n-build:
	$(POETRY) run pybabel compile -d locales -D quantsentinel

coverage-domain-services:
	$(POETRY) run pytest --cov=src/quantsentinel --cov-report=json --cov-report=term-missing --cov-fail-under=0 --cov-fail-under=0
	$(POETRY) run python scripts/check_domain_services_coverage.py --report coverage.json --min 90

ci:
	$(POETRY) run ruff check $(RUFF_SCOPE)
	$(POETRY) run pytest --cov=src/quantsentinel --cov-report=json --cov-report=term-missing --cov-fail-under=0 --cov-fail-under=0
	$(POETRY) run python scripts/check_domain_services_coverage.py --report coverage.json --min 90

acceptance:
	bash scripts/acceptance_oneclick.sh
