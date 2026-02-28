"""
SQLAlchemy ORM models (system-of-record).

Rules:
- This module defines ONLY database models + enums + table constraints.
- No business logic, no services, no Streamlit.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# -----------------------------
# Base & mixins
# -----------------------------


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


# -----------------------------
# Enums
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


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)

    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    default_language: Mapped[str] = mapped_column(String(32), nullable=False, server_default="en")

    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # relationships
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="actor", cascade="all, delete-orphan")
    tasks: Mapped[list["Task"]] = relationship(back_populates="actor", cascade="all, delete-orphan")
    layout_presets: Mapped[list["UILayoutPreset"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:  # pragma: no cover
        return f"User(id={self.id}, username={self.username!r}, role={self.role.value!r})"


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(128), nullable=True, index=True)

    payload_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")

    actor: Mapped[User | None] = relationship(back_populates="audit_logs")

    def __repr__(self) -> str:  # pragma: no cover
        return f"AuditLog(id={self.id}, action={self.action!r}, entity_type={self.entity_type!r})"


class Task(Base, TimestampMixin):
    """
    Background task tracking (Celery + UI visibility).

    Stores coarse progress and details; detailed logs can also be saved as artifacts.
    """

    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    task_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus, name="task_status"), nullable=False, index=True)

    progress: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")  # 0..100

    detail: Mapped[str] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    actor: Mapped[User | None] = relationship(back_populates="tasks")


class Instrument(Base, TimestampMixin):
    __tablename__ = "instruments"

    ticker: Mapped[str] = mapped_column(String(64), primary_key=True)

    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    exchange: Mapped[str | None] = mapped_column(String(64), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(16), nullable=True)

    is_watched: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    source: Mapped[str | None] = mapped_column(String(64), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"Instrument(ticker={self.ticker!r}, watched={self.is_watched})"


class PriceDaily(Base):
    __tablename__ = "prices_daily"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    ticker: Mapped[str] = mapped_column(String(64), ForeignKey("instruments.ticker", ondelete="CASCADE"), nullable=False)
    date: Mapped[datetime] = mapped_column(Date, nullable=False)

    open: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    high: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    low: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    close: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    adj_close: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    volume: Mapped[float | None] = mapped_column(Numeric(24, 2), nullable=True)

    source: Mapped[str] = mapped_column(String(64), nullable=False, server_default="unknown")
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    revision_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True, default=uuid.uuid4)

    __table_args__ = (
        UniqueConstraint("ticker", "date", name="uq_prices_daily_ticker_date"),
        Index("ix_prices_daily_ticker_date", "ticker", "date"),
    )


class Recipe(Base, TimestampMixin):
    """
    Recipe defines derived series / indicator computations (versioned & reproducible).
    """

    __tablename__ = "recipes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    kind: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    params_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")


class DerivedDaily(Base):
    __tablename__ = "derived_daily"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    ticker: Mapped[str] = mapped_column(String(64), ForeignKey("instruments.ticker", ondelete="CASCADE"), nullable=False)
    date: Mapped[datetime] = mapped_column(Date, nullable=False)

    field: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[float | None] = mapped_column(Numeric(24, 10), nullable=True)

    recipe_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("recipes.id"), nullable=True)
    revision_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint("ticker", "date", "field", name="uq_derived_daily_ticker_date_field"),
        Index("ix_derived_daily_ticker_field", "ticker", "field"),
    )


class AlertRule(Base, TimestampMixin):
    __tablename__ = "alert_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    scope_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    params_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")

    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    severity: Mapped[str] = mapped_column(String(16), nullable=False, server_default="MEDIUM")

    # governance fields
    dedup_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    silenced_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    rule_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("alert_rules.id", ondelete="CASCADE"), nullable=False)
    ticker: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    event_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    asof_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)

    message: Mapped[str] = mapped_column(Text, nullable=False)
    context_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")

    status: Mapped[AlertEventStatus] = mapped_column(
        Enum(AlertEventStatus, name="alert_event_status"),
        nullable=False,
        server_default=AlertEventStatus.NEW.value,
        index=True,
    )
    ack_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ack_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (Index("ix_alert_events_rule_ts", "rule_id", "event_ts"),)


class StrategyProject(Base, TimestampMixin):
    __tablename__ = "strategy_projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class StrategyRun(Base, TimestampMixin):
    __tablename__ = "strategy_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("strategy_projects.id", ondelete="SET NULL"), nullable=True, index=True
    )

    family: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    params_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    metrics_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    artifacts_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")

    start_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)

    score: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)

    data_revision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    code_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    random_seed: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (Index("ix_strategy_runs_project_created", "project_id", "created_at"),)


class RefreshLog(Base):
    __tablename__ = "refresh_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    run_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    ticker: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    last_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)

    revision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)


class UILayoutPreset(Base, TimestampMixin):
    __tablename__ = "ui_layout_presets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    user: Mapped[User] = relationship(back_populates="layout_presets")

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    workspace: Mapped[LayoutWorkspace] = mapped_column(Enum(LayoutWorkspace, name="layout_workspace"), nullable=False, index=True)

    layout_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    __table_args__ = (
        UniqueConstraint("user_id", "workspace", "name", name="uq_layout_user_workspace_name"),
        Index("ix_layout_user_workspace_default", "user_id", "workspace", "is_default"),
    )