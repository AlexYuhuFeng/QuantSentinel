# Contributing to QuantSentinel

This is a production-grade engineering project. Experimental or loosely structured code is not accepted.

---

## 1. Pull Request Rules

Every PR must include:

- Clear description of change
- List of modified files
- Tests added
- Risk assessment
- Rollback plan (if applicable)

---

## 2. File Modification Restrictions

When working on a feature:

- Modify only files declared in the issue.
- If additional files are required, update the issue before proceeding.
- No silent cross-layer refactoring.

---

## 3. Testing Requirements

Every new feature must include:

- Unit tests (`domain`)
- Service-level integration tests
- Failure-case coverage

---

## 4. No Feature Claims Without Implementation

`README.md` must not describe capabilities that are not implemented.

---

## 5. Code Style

- Python 3.12+
- Type hints required
- Docstrings required for public functions
- Pydantic for validation
- SQLAlchemy 2.0 style only

---

## 6. Commit Message Style

Use Conventional Commits, such as:

- `feat:`
- `fix:`
- `refactor:`
- `test:`
- `chore:`

---

## 7. AI Agent Usage Policy

AI agents must:

- Follow `ARCHITECTURE.md` strictly
- Not modify files outside declared scope
- Not introduce hidden dependencies
- Not fabricate functionality

Failure to comply invalidates the PR.
