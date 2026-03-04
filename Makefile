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
	tests/unit/services/test_strategy_family_matrix.py \
	tests/integration/db/test_migrations_contract.py \
	tests/integration/tasks/test_task_enqueue_integration.py \
	tests/integration/test_rbac_gating.py \
	tests/integration/i18n/test_language_switch_snapshots.py \
	tests/integration/layout/test_layout_service_integration.py
COV_SCOPE = \
	--cov=quantsentinel.domain.market.indicators \
	--cov=quantsentinel.domain.alerts.rules \
	--cov=quantsentinel.domain.alerts.expression \
	--cov=quantsentinel.domain.research.walk_forward \
	--cov=quantsentinel.domain.research.metrics \
	--cov=quantsentinel.services.strategy_service

lint:
	$(POETRY) run ruff check $(RUFF_SCOPE)

test:
	$(POETRY) run pytest $(COV_SCOPE) --cov-report=term-missing

i18n-check:
	$(POETRY) run python scripts/check_missing_translations.py $(PO_FILE)
	$(POETRY) run python scripts/check_streamlit_i18n.py

i18n-build:
	$(POETRY) run pybabel compile -d locales -D quantsentinel

coverage-domain-services:
	$(POETRY) run pytest $(COV_SCOPE) --cov-report=term-missing

ci:
	$(POETRY) run ruff check $(RUFF_SCOPE)
	$(POETRY) run pytest $(COV_SCOPE) --cov-report=term-missing

acceptance:
	bash scripts/acceptance_oneclick.sh
