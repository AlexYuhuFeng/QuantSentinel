# Copilot / AI Agent Instructions

You are working on QuantSentinel.

## Strict Rules

1. Follow `ARCHITECTURE.md` dependency direction.
2. Do not move business logic into UI.
3. Do not import `infra` from `domain`.
4. Do not invent features that are not implemented.
5. Every new file must include tests.
6. All UI text must use i18n.
7. All write operations must generate audit log entries.
8. Background tasks must update `tasks` table status.
9. Do not modify files outside declared scope.
10. If uncertain, stop and ask.

## Before Finishing Any Task

- Run `ruff`
- Run `pytest`
- Verify Alembic migration works

If any of these checks fail, fix them before completion.
