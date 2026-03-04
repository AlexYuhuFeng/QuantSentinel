#!/usr/bin/env bash
set -euo pipefail

# One-click acceptance workflow for local Docker deployment.
# Usage:
#   bash scripts/acceptance_oneclick.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

log() { printf '\n[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }

log "Starting stack"
docker compose up -d

log "Waiting services"
docker compose ps

log "Running acceptance validation sequence"
# 1) 登录 + 默认管理员引导
poetry run pytest tests/integration/app_smoke/test_default_admin_bootstrap.py -q
# 2) 导入/规则/策略/任务日志（基于服务与页面集成）
poetry run pytest tests/integration/app_smoke/test_palette_shortcuts_audit_integration.py -q
# 3) 快捷键 + 命令面板
poetry run pytest tests/integration/app_smoke/test_shortcuts.py tests/unit/app/test_command_palette.py -q
# 4) 布局保存/加载
poetry run pytest tests/integration/layout/test_layout_service_integration.py -q
# 5) i18n 切换
poetry run pytest tests/integration/i18n/test_language_switch_snapshots.py -q
# 6) 任务队列日志与入队
poetry run pytest tests/integration/tasks/test_task_enqueue_integration.py -q

log "Acceptance checks completed"
