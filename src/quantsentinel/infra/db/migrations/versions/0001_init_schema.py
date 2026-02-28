"""init schema

Revision ID: 0001_init_schema
Revises:
Create Date: 2026-02-28

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001_init_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---- enums ----
    user_role = sa.Enum("Admin", "Editor", "Viewer", name="user_role")
    task_status = sa.Enum("PENDING", "RUNNING", "SUCCESS", "FAILED", "CANCELED", name="task_status")
    alert_event_status = sa.Enum("NEW", "ACKED", name="alert_event_status")
    layout_workspace = sa.Enum("Market", "Explore", "Monitor", "Research", "Strategy", name="layout_workspace")

    bind = op.get_bind()
    user_role.create(bind, checkfirst=True)
    task_status.create(bind, checkfirst=True)
    alert_event_status.create(bind, checkfirst=True)
    layout_workspace.create(bind, checkfirst=True)

    # ---- tables ----
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("default_language", sa.String(length=32), nullable=False, server_default=sa.text("'en'")),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("username", name="uq_users_username"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=128), nullable=True),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_index("ix_audit_log_actor_id", "audit_log", ["actor_id"])
    op.create_index("ix_audit_log_action", "audit_log", ["action"])
    op.create_index("ix_audit_log_entity_type", "audit_log", ["entity_type"])
    op.create_index("ix_audit_log_entity_id", "audit_log", ["entity_id"])

    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("status", task_status, nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_tasks_task_type", "tasks", ["task_type"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_actor_id", "tasks", ["actor_id"])

    op.create_table(
        "instruments",
        sa.Column("ticker", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("exchange", sa.String(length=64), nullable=True),
        sa.Column("currency", sa.String(length=16), nullable=True),
        sa.Column("is_watched", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("source", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "prices_daily",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.String(length=64), sa.ForeignKey("instruments.ticker", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("open", sa.Numeric(18, 8), nullable=True),
        sa.Column("high", sa.Numeric(18, 8), nullable=True),
        sa.Column("low", sa.Numeric(18, 8), nullable=True),
        sa.Column("close", sa.Numeric(18, 8), nullable=True),
        sa.Column("adj_close", sa.Numeric(18, 8), nullable=True),
        sa.Column("volume", sa.Numeric(24, 2), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False, server_default=sa.text("'unknown'")),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("revision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.UniqueConstraint("ticker", "date", name="uq_prices_daily_ticker_date"),
    )
    op.create_index("ix_prices_daily_ticker_date", "prices_daily", ["ticker", "date"])
    op.create_index("ix_prices_daily_revision_id", "prices_daily", ["revision_id"])

    op.create_table(
        "recipes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("params_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_recipes_kind", "recipes", ["kind"])

    op.create_table(
        "derived_daily",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.String(length=64), sa.ForeignKey("instruments.ticker", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("field", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Numeric(24, 10), nullable=True),
        sa.Column("recipe_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("recipes.id"), nullable=True),
        sa.Column("revision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.UniqueConstraint("ticker", "date", "field", name="uq_derived_daily_ticker_date_field"),
    )
    op.create_index("ix_derived_daily_ticker_field", "derived_daily", ["ticker", "field"])
    op.create_index("ix_derived_daily_revision_id", "derived_daily", ["revision_id"])

    op.create_table(
        "alert_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("rule_type", sa.String(length=64), nullable=False),
        sa.Column("scope_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("params_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("severity", sa.String(length=16), nullable=False, server_default=sa.text("'MEDIUM'")),
        sa.Column("dedup_key", sa.String(length=128), nullable=True),
        sa.Column("silenced_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_alert_rules_rule_type", "alert_rules", ["rule_type"])
    op.create_index("ix_alert_rules_dedup_key", "alert_rules", ["dedup_key"])

    op.create_table(
        "alert_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alert_rules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ticker", sa.String(length=64), nullable=False),
        sa.Column("event_ts", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("asof_date", sa.Date(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("context_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", alert_event_status, nullable=False, server_default=sa.text("'NEW'")),
        sa.Column("ack_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ack_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_alert_events_ticker", "alert_events", ["ticker"])
    op.create_index("ix_alert_events_status", "alert_events", ["status"])
    op.create_index("ix_alert_events_rule_ts", "alert_events", ["rule_id", "event_ts"])

    op.create_table(
        "strategy_projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_strategy_projects_name", "strategy_projects", ["name"])

    op.create_table(
        "strategy_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("strategy_projects.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("family", sa.String(length=64), nullable=False),
        sa.Column("params_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("metrics_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("artifacts_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("score", sa.Numeric(18, 8), nullable=True),
        sa.Column("data_revision_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("code_hash", sa.String(length=64), nullable=True),
        sa.Column("random_seed", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_strategy_runs_family", "strategy_runs", ["family"])
    op.create_index("ix_strategy_runs_project_created", "strategy_runs", ["project_id", "created_at"])
    op.create_index("ix_strategy_runs_data_revision_id", "strategy_runs", ["data_revision_id"])

    op.create_table(
        "refresh_log",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("run_ts", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("ticker", sa.String(length=64), nullable=True),
        sa.Column("last_date", sa.Date(), nullable=True),
        sa.Column("revision_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_refresh_log_ticker", "refresh_log", ["ticker"])
    op.create_index("ix_refresh_log_revision_id", "refresh_log", ["revision_id"])

    op.create_table(
        "ui_layout_presets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("workspace", layout_workspace, nullable=False),
        sa.Column("layout_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "workspace", "name", name="uq_layout_user_workspace_name"),
    )
    op.create_index("ix_layout_user_workspace_default", "ui_layout_presets", ["user_id", "workspace", "is_default"])


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_index("ix_layout_user_workspace_default", table_name="ui_layout_presets")
    op.drop_table("ui_layout_presets")

    op.drop_index("ix_refresh_log_revision_id", table_name="refresh_log")
    op.drop_index("ix_refresh_log_ticker", table_name="refresh_log")
    op.drop_table("refresh_log")

    op.drop_index("ix_strategy_runs_data_revision_id", table_name="strategy_runs")
    op.drop_index("ix_strategy_runs_project_created", table_name="strategy_runs")
    op.drop_index("ix_strategy_runs_family", table_name="strategy_runs")
    op.drop_table("strategy_runs")

    op.drop_index("ix_strategy_projects_name", table_name="strategy_projects")
    op.drop_table("strategy_projects")

    op.drop_index("ix_alert_events_rule_ts", table_name="alert_events")
    op.drop_index("ix_alert_events_status", table_name="alert_events")
    op.drop_index("ix_alert_events_ticker", table_name="alert_events")
    op.drop_table("alert_events")

    op.drop_index("ix_alert_rules_dedup_key", table_name="alert_rules")
    op.drop_index("ix_alert_rules_rule_type", table_name="alert_rules")
    op.drop_table("alert_rules")

    op.drop_index("ix_derived_daily_revision_id", table_name="derived_daily")
    op.drop_index("ix_derived_daily_ticker_field", table_name="derived_daily")
    op.drop_table("derived_daily")

    op.drop_index("ix_recipes_kind", table_name="recipes")
    op.drop_table("recipes")

    op.drop_index("ix_prices_daily_revision_id", table_name="prices_daily")
    op.drop_index("ix_prices_daily_ticker_date", table_name="prices_daily")
    op.drop_table("prices_daily")

    op.drop_table("instruments")

    op.drop_index("ix_tasks_actor_id", table_name="tasks")
    op.drop_index("ix_tasks_status", table_name="tasks")
    op.drop_index("ix_tasks_task_type", table_name="tasks")
    op.drop_table("tasks")

    op.drop_index("ix_audit_log_entity_id", table_name="audit_log")
    op.drop_index("ix_audit_log_entity_type", table_name="audit_log")
    op.drop_index("ix_audit_log_action", table_name="audit_log")
    op.drop_index("ix_audit_log_actor_id", table_name="audit_log")
    op.drop_table("audit_log")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")

    # Drop enums after all tables
    bind = op.get_bind()
    sa.Enum(name="layout_workspace").drop(bind, checkfirst=True)
    sa.Enum(name="alert_event_status").drop(bind, checkfirst=True)
    sa.Enum(name="task_status").drop(bind, checkfirst=True)
    sa.Enum(name="user_role").drop(bind, checkfirst=True)