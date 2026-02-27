# QuantSentinel Architecture

This document defines the architectural boundaries and non-negotiable rules
for QuantSentinel. All contributors and AI agents must follow this strictly.

---

# 1. High-Level Architecture

QuantSentinel follows a strict layered architecture:
app → services → (domain + infra) → common
i18n → common

## Dependency Rules (STRICT)

- `app` may import `services`, `i18n`, `common`
- `services` may import `domain`, `infra`, `common`
- `infra` may import `common`
- `domain` may import `common`
- `common` may not import anything from other layers

### FORBIDDEN:

- domain importing sqlalchemy, celery, streamlit, redis
- UI logic in services
- business logic in infra
- DB access inside domain
- calling Celery from UI directly

Violation of these rules = PR rejection.

---

# 2. Layer Responsibilities

## app/
UI only (Streamlit)
- Layout
- Routing
- RBAC gating (visual only)
- Calling services
- Displaying data

No business logic allowed.

---

## services/
Use-case orchestration layer.
- Input validation (pydantic)
- Permission checking
- Transaction management
- Audit logging
- Calling domain logic
- Calling repos
- Dispatching background tasks

Services must not contain raw SQL.

---

## domain/
Pure business logic.
- Indicators
- Backtesting engine
- Risk calculations
- Alert evaluation
- Walk-forward
- Expression parser

Domain must be:
- Deterministic
- Pure or near-pure
- Fully unit testable
- No IO

---

## infra/
Infrastructure adapters.
- Database (SQLAlchemy)
- Repositories (CRUD only)
- Celery tasks
- Providers (Yahoo, CSV)
- Artifact storage

Infra must not contain business rules.

---

## common/
Shared utilities.
- Errors
- Config
- Logging
- Security
- ID generation
- Time utilities

---

# 3. Database Design Principles

- PostgreSQL is the source of truth.
- All writes must go through services.
- Every write must generate audit log entry.
- All background tasks must record status in `tasks` table.

---

# 4. Background Task Model

Celery workers must:

- Only call service layer.
- Never directly manipulate DB models.
- Always update task status.
- Fail safely with retry policies.

---

# 5. i18n Rules

- All UI strings must go through gettext.
- No hardcoded UI text allowed.
- Snapshot exports must respect user language.
- Locale files must live under `/locales`.

---

# 6. Testing Philosophy

Minimum coverage:
- domain + services >= 90%

Testing layers:
- unit: domain
- integration: services + infra
- smoke: app boot + RBAC

---

# 7. Non-Negotiable Quality Gates

Before merge:
- ruff passes
- pytest passes
- alembic upgrade head succeeds
- docker compose up works

---

If unsure about where code belongs:
Default rule = move logic DOWNWARD (towards domain), not upward.
