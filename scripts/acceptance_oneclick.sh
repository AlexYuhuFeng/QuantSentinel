#!/usr/bin/env bash
set -Eeuo pipefail

# One-click acceptance workflow for local Docker deployment.
# Usage:
#   bash scripts/acceptance_oneclick.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/artifacts/acceptance"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$LOG_DIR/acceptance_${TIMESTAMP}.log"
SUMMARY_FILE="$LOG_DIR/acceptance_${TIMESTAMP}.summary.log"

mkdir -p "$LOG_DIR"
cd "$ROOT_DIR"

log() {
  local level="$1"
  shift
  local message="$*"
  printf '[%s] [%s] %s\n' "$(date +'%Y-%m-%d %H:%M:%S')" "$level" "$message" | tee -a "$LOG_FILE"
}

run_step() {
  local name="$1"
  shift
  log "STEP" "START | ${name}"
  if "$@" >>"$LOG_FILE" 2>&1; then
    log "PASS" "${name}"
    printf 'PASS | %s\n' "$name" >>"$SUMMARY_FILE"
  else
    local exit_code=$?
    log "FAIL" "${name} (exit=${exit_code})"
    printf 'FAIL | %s | exit=%s\n' "$name" "$exit_code" >>"$SUMMARY_FILE"
    return "$exit_code"
  fi
}

run_step "Docker Compose build & start" docker compose up -d --build
run_step "Docker Compose status" docker compose ps
run_step "DB migration (web container)" docker compose exec -T web alembic -c /app/alembic.ini upgrade head
run_step "Admin bootstrap/login smoke" env PYTHONPATH=src poetry run pytest tests/integration/app_smoke/test_default_admin_bootstrap.py -q
run_step "Data import smoke" env PYTHONPATH=src poetry run pytest tests/integration/app_smoke/test_explore_page_data_flow.py -q
run_step "Rules execution smoke" env PYTHONPATH=src poetry run pytest tests/integration/tasks/test_alerts_governance_integration.py -q
run_step "Strategy + param search smoke" env PYTHONPATH=src poetry run pytest tests/integration/tasks/test_param_search_pipeline.py -q
run_step "Snapshot export smoke" env PYTHONPATH=src poetry run pytest tests/integration/tasks/test_snapshot_export_artifacts.py -q
run_step "Language switch smoke" env PYTHONPATH=src poetry run pytest tests/integration/i18n/test_language_switch_snapshots.py -q
run_step "Shortcut + command palette smoke" env PYTHONPATH=src poetry run pytest tests/integration/app_smoke/test_shortcuts.py tests/unit/app/test_command_palette.py -q

log "DONE" "Acceptance checks completed"
log "DONE" "Summary: $SUMMARY_FILE"
