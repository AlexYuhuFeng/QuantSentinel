from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# -----------------------------
# Enums (must match DB enum types)
# -----------------------------

class UserRole(str, enum.Enum):
    ADMIN = "Admin"
    EDITOR = "Editor"
    VIEWER = "Viewer"


class TaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class AlertEventStatus(str, enum.Enum):
    NEW = "NEW"
    ACKED = "ACKED"


class LayoutWorkspace(str, enum.Enum):
    MARKET = "Market"
    EXPLORE = "Explore"
    MONITOR = "Monitor"
    RESEARCH = "Research"
    STRATEGY = "Strategy"


# -----------------------------
# Core tables
# -----------------------------

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role", native_enum=True),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    default_language: Mapped[str] = mapped_column(String(32), nullable=False, server_default="en")

    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    payload_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")

    actor: Mapped[User | None] = relationship("User", lazy="joined")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)

    status: Mapped[TaskStatus] = mapped_column(
        SAEnum(TaskStatus, name="task_status", native_enum=True),
        nullable=False,
    )
    progress: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    actor: Mapped[User | None] = relationship("User", lazy="joined")


class Instrument(Base):
    __tablename__ = "instruments"

    ticker: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    exchange: Mapped[str | None] = mapped_column(String(64), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(16), nullable=True)

    is_watched: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class PriceDaily(Base):
    __tablename__ = "prices_daily"
    __table_args__ = (UniqueConstraint("ticker", "date", name="uq_prices_daily_ticker_date"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    ticker: Mapped[str] = mapped_column(
        String(64), ForeignKey("instruments.ticker", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)

    open: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    high: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    low: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    close: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    adj_close: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)

    volume: Mapped[Decimal | None] = mapped_column(Numeric(24, 2), nullable=True)

    source: Mapped[str] = mapped_column(String(64), nullable=False, server_default="unknown")
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    revision_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)

    instrument: Mapped[Instrument] = relationship("Instrument", lazy="joined")


# -----------------------------
# Derived/recipes
# -----------------------------

class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    params_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class DerivedDaily(Base):
    __tablename__ = "derived_daily"
    __table_args__ = (UniqueConstraint("ticker", "date", "field", name="uq_derived_daily_ticker_date_field"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    ticker: Mapped[str] = mapped_column(
        String(64), ForeignKey("instruments.ticker", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    field: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[Decimal | None] = mapped_column(Numeric(24, 10), nullable=True)

    recipe_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("recipes.id"), nullable=True
    )

    revision_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)


# -----------------------------
# Alerts
# -----------------------------

class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(64), nullable=False)

    scope_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    params_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")

    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    severity: Mapped[str] = mapped_column(String(16), nullable=False, server_default="MEDIUM")

    dedup_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    silenced_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    creator: Mapped[User | None] = relationship("User", lazy="joined")


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    rule_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("alert_rules.id", ondelete="CASCADE"), nullable=False
    )

    ticker: Mapped[str] = mapped_column(String(64), nullable=False)

    event_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    asof_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    message: Mapped[str] = mapped_column(Text, nullable=False)
    context_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")

    status: Mapped[AlertEventStatus] = mapped_column(
        SAEnum(AlertEventStatus, name="alert_event_status", native_enum=True),
        nullable=False,
        server_default="NEW",
    )

    ack_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ack_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    rule: Mapped[AlertRule] = relationship("AlertRule", lazy="joined")
    acker: Mapped[User | None] = relationship("User", lazy="joined")


# -----------------------------
# Strategy projects/runs
# -----------------------------

class StrategyProject(Base):
    __tablename__ = "strategy_projects"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class StrategyRun(Base):
    __tablename__ = "strategy_runs"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    project_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("strategy_projects.id", ondelete="SET NULL"), nullable=True
    )

    family: Mapped[str] = mapped_column(String(64), nullable=False)
    params_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    metrics_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    artifacts_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")

    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    score: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)

    data_revision_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    code_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    random_seed: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    project: Mapped[StrategyProject | None] = relationship("StrategyProject", lazy="joined")


# -----------------------------
# Refresh log
# -----------------------------

class RefreshLog(Base):
    __tablename__ = "refresh_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    ticker: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    revision_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)


# -----------------------------
# UI layout presets
# -----------------------------

class UILayoutPreset(Base):
    __tablename__ = "ui_layout_presets"
    __table_args__ = (UniqueConstraint("user_id", "workspace", "name", name="uq_layout_user_workspace_name"),)

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(128), nullable=False)

    workspace: Mapped[LayoutWorkspace] = mapped_column(
        SAEnum(LayoutWorkspace, name="layout_workspace", native_enum=True),
        nullable=False,
    )

    layout_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship("User", lazy="joined")


# -----------------------------
# Notifications (needs a new migration 0002)
# -----------------------------

class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    status: Mapped[str] = mapped_column(String(16), nullable=False)  # PENDING/SENT/FAILED

    recipients_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default="[]")
    channels_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default="[]")

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    severity: Mapped[str] = mapped_column(String(16), nullable=False, server_default="MEDIUM")

    tags_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default="[]")
    context_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")

    dedup_key: Mapped[str | None] = mapped_column(String(128), nullable=True)

    related_entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    related_entity_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )