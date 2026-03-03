from __future__ import annotations

import uuid

import streamlit as st

from quantsentinel.app.ui.state import auth, push_toast
from quantsentinel.i18n.gettext import get_translator
from quantsentinel.infra.db.models import AlertEventStatus, AlertRule
from quantsentinel.services.alerts_service import AlertsService
from quantsentinel.services.task_service import TaskService
from quantsentinel.services.notification_service import (
    NotificationService,
    NotificationPayload,
)

# ----------------------------------------------------------------------------
# Monitor Page — Manage Alert Rules + View Alert Events
# ----------------------------------------------------------------------------

def render() -> None:
    """
    Page entrypoint — displays current alerts, active rules,
    and alert events, plus controls to run monitoring cycles.
    """
    a = auth()
    t = get_translator(a.language)

    st.markdown(f"## {t('Monitor Alerts')}")

    # Header buttons
    col_run, col_refresh = st.columns([1, 1])
    with col_run:
        if st.button(t("Run Monitor Now")):
            _run_monitor_cycle(t)
    with col_refresh:
        if st.button(t("Refresh Alerts")):
            st.experimental_rerun()

    st.divider()

    _render_rules_section(t)
    st.divider()
    _render_events_section(t)


# -----------------------------------
# ALERT RULES
# -----------------------------------

def _render_rules_section(t) -> None:
    st.header(t("Alert Rules"))

    alerts_svc = AlertsService()
    rules = alerts_svc.list_enabled_rules()

    if not rules:
        st.info(t("No alert rules defined."))
        return

    for rule in rules:
        with st.expander(f"{rule.name} — {rule.rule_type}"):
            _render_single_rule(rule, t)


def _render_single_rule(rule: AlertRule, t) -> None:
    st.write(f"📌 **{t('Rule Name')}:** {rule.name}")
    st.write(f"🧩 **{t('Rule Type')}:** {rule.rule_type}")
    st.write(f"⚙️ **{t('Params')}:** {rule.params_json}")
    st.write(f"📍 **{t('Scope')}:** {rule.scope_json}")
    st.write(f"🚦 **{t('Enabled')}:** {rule.enabled}")

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button(t("Disable") if rule.enabled else t("Enable"), key=f"toggle_rule_{rule.id}"):
            alerts_svc.set_rule_enabled(rule_id=rule.id, enabled=not rule.enabled)
            push_toast("success", t("Rule updated."))
            st.experimental_rerun()

    with col2:
        if st.button(t("Silence Rule"), key=f"silence_rule_{rule.id}"):
            # Silences for 1 hour by default
            alerts_svc.set_rule_silenced(rule_id=rule.id, duration_minutes=60)
            push_toast("info", t("Rule silenced"))
            st.experimental_rerun()

    with col3:
        if st.button(t("Delete Rule"), key=f"del_rule_{rule.id}"):
            alerts_svc.delete_rule(rule_id=rule.id)
            push_toast("warning", t("Rule deleted."))
            st.experimental_rerun()


# -----------------------------------
# ALERT EVENTS
# -----------------------------------

def _render_events_section(t) -> None:
    st.header(t("Recent Alert Events"))

    alerts_svc = AlertsService()
    events = alerts_svc.list_recent_events(limit=100)

    if not events:
        st.info(t("No alert events to display."))
        return

    for ev in events:
        _render_single_event(ev, t)


def _render_single_event(ev: object, t) -> None:
    """
    A single alert event item.
    """
    ts = ev.event_ts.strftime("%Y-%m-%d %H:%M:%S")
    status = ev.status

    with st.container():
        st.write(
            f"📅 **{t('Time')}:** {ts}  |  "
            f"📌 **{t('Ticker')}:** {ev.ticker}  |  "
            f"🧠 **{t('Rule')}:** {ev.rule.name}"
        )

        st.write(f"💬 **{t('Message')}:** {ev.message}")

        if status == AlertEventStatus.NEW:
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button(t("Acknowledge"), key=f"ack_{ev.id}"):
                    _ack_event(ev.id, t)
            with col2:
                if st.button(t("Notify"), key=f"notify_{ev.id}"):
                    _notify_event(ev, t)
        else:
            st.caption(f"{t('Status')}: {status.value}")


# -----------------------------------
# BACKEND ACTIONS
# -----------------------------------

def _run_monitor_cycle(t) -> None:
    """
    Run a monitor cycle via TaskService, start background task.
    """
    task_svc = TaskService()
    try:
        task_id = task_svc.create_task(task_type="alert_monitor_cycle")
        task_svc.start_task(task_id)
        push_toast("success", t("Monitor cycle started."))
    except Exception as e:
        push_toast("error", f"{t('Failed to start monitor')}: {e}")


def _ack_event(event_id: uuid.UUID, t) -> None:
    """
    Acknowledge a single alert event.
    """
    try:
        svc = AlertsService()
        svc.ack_event(event_id=event_id)
        push_toast("success", t("Alert acknowledged."))
        st.experimental_rerun()
    except Exception as e:
        push_toast("error", f"{t('Failed to acknowledge')}: {e}")


def _notify_event(ev: object, t) -> None:
    """
    Trigger a notification for an alert event.
    """
    try:
        notif_svc = NotificationService()
        payload = NotificationPayload(
            title=f"{t('Alert')}: {ev.rule.name}",
            body=ev.message,
            severity=ev.rule.severity,
            tags=[ev.ticker],
            context={"event_id": str(ev.id)},
        )
        notif_svc.create(
            actor_id=None,
            recipients=[ev.ticker],  # replace with real user IDs/contacts
            channels=["email", "wechat"],
            payload=payload,
            dedup_key=str(ev.id),
            related_entity_type="alert_event",
            related_entity_id=str(ev.id),
        )
        push_toast("success", t("Notification queued."))
    except Exception as e:
        push_toast("error", f"{t('Failed to notify')}: {e}")