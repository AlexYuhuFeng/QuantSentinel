from __future__ import annotations

import uuid

import streamlit as st

from quantsentinel.app.ui.components import render_empty_state, render_error_state, render_success_state
from quantsentinel.app.ui.drawer import Drawer
from quantsentinel.app.ui.layout import render_workspace_shell
from quantsentinel.app.ui.state import auth, push_toast
from quantsentinel.i18n.gettext import get_translator
from quantsentinel.infra.db.models import AlertEventStatus, AlertRule
from quantsentinel.infra.db.repos.alerts_repo import AlertRuleCreate
from quantsentinel.services.alerts_service import AlertsService
from quantsentinel.services.notification_service import NotificationPayload, NotificationService
from quantsentinel.services.task_service import TaskService


def render() -> None:
    t = get_translator(auth().language)

    def _render_toolbar() -> None:
        st.markdown(f"## {t('Monitor Alerts')}")
        col_run, col_refresh = st.columns([1, 1])
        with col_run:
            if st.button(t("Run Monitor Now")):
                _run_monitor_cycle(t)
        with col_refresh:
            if st.button(t("Refresh Alerts")):
                st.rerun()

    def _render_main() -> None:
        _render_rule_wizard(t)
        st.divider()
        _render_rules_section(t)
        st.divider()
        _render_events_section(t)
        st.divider()
        _render_recent_tasks_section(t)

    def _render_drawer() -> None:
        Drawer.render(title=t("Details"))

    render_workspace_shell(render_toolbar=_render_toolbar, render_main=_render_main, render_drawer=_render_drawer)


def _render_rule_wizard(t) -> None:
    st.subheader(t("Create Alert Rule Wizard"))
    step = st.session_state.get("monitor_rule_wizard_step", 1)
    st.caption(f"{t('Step')} {step}/4")

    if step == 1:
        name = st.text_input(t("Rule Name"), key="wizard_name")
        st.selectbox(t("Rule Type"), options=sorted(AlertsService.SUPPORTED_RULE_TYPES), key="wizard_type")
        if st.button(t("Next"), key="wizard_step1_next"):
            if not name.strip():
                st.error(t("Rule name is required."))
            else:
                st.session_state["monitor_rule_wizard_step"] = 2
                st.rerun()

    elif step == 2:
        st.text_input(t("Scope Tickers (comma separated)"), key="wizard_scope")
        st.number_input(t("Dedup Minutes"), min_value=1, value=60, key="wizard_dedup")
        st.number_input(t("Silence Minutes"), min_value=0, value=0, key="wizard_silence")
        st.text_input(t("Aggregation Key (optional)"), key="wizard_aggregation")
        col_prev, col_next = st.columns(2)
        with col_prev:
            if st.button(t("Back"), key="wizard_step2_prev"):
                st.session_state["monitor_rule_wizard_step"] = 1
                st.rerun()
        with col_next:
            if st.button(t("Next"), key="wizard_step2_next"):
                st.session_state["monitor_rule_wizard_step"] = 3
                st.rerun()

    elif step == 3:
        _render_params_by_type(t)
        col_prev, col_next = st.columns(2)
        with col_prev:
            if st.button(t("Back"), key="wizard_step3_prev"):
                st.session_state["monitor_rule_wizard_step"] = 2
                st.rerun()
        with col_next:
            if st.button(t("Preview"), key="wizard_step3_preview"):
                error = _validate_wizard_inputs()
                if error:
                    st.error(t(error))
                else:
                    st.session_state["monitor_rule_wizard_step"] = 4
                    st.rerun()

    else:
        preview = _build_preview_payload()
        st.markdown(f"**{t('Preview & Confirm')}**")
        st.json(preview)
        col_prev, col_submit = st.columns(2)
        with col_prev:
            if st.button(t("Back"), key="wizard_step4_prev"):
                st.session_state["monitor_rule_wizard_step"] = 3
                st.rerun()
        with col_submit:
            if st.button(t("Create Rule"), key="wizard_submit"):
                _submit_wizard_rule(t)


def _render_params_by_type(t) -> None:
    rule_type = st.session_state.get("wizard_type", "threshold")
    st.markdown(f"**{t('Rule Parameters')}**")
    if rule_type == "threshold":
        st.selectbox(t("Operator"), ["<", ">"], key="wizard_operator")
        st.number_input(t("Threshold Value"), value=0.0, key="wizard_threshold_value")
    elif rule_type == "z_score":
        st.number_input(t("Lookback"), min_value=5, value=20, key="wizard_lookback")
        st.number_input(t("Z Threshold"), min_value=0.1, value=2.0, key="wizard_z_threshold")
    elif rule_type == "volatility":
        st.number_input(t("Lookback"), min_value=5, value=20, key="wizard_lookback")
        st.number_input(t("Vol Threshold"), min_value=0.001, value=0.03, key="wizard_vol_threshold")
    elif rule_type == "staleness":
        st.number_input(t("Max Days"), min_value=1, value=7, key="wizard_max_days")
    elif rule_type == "missing_data":
        st.number_input(t("Lookback Days"), min_value=1, value=30, key="wizard_lookback_days")
        st.number_input(t("Minimum Points"), min_value=1, value=25, key="wizard_min_points")
    elif rule_type == "correlation_break":
        st.text_input(t("Benchmark Ticker"), key="wizard_benchmark")
        st.number_input(t("Lookback"), min_value=5, value=20, key="wizard_lookback")
        st.number_input(t("Min Correlation"), min_value=-1.0, max_value=1.0, value=0.2, key="wizard_min_corr")
    elif rule_type == "custom_expression":
        st.text_input(t("Expression"), key="wizard_expression", help="Variables: close, ret, vol, z, ma20, ma60")


def _validate_wizard_inputs() -> str | None:
    params = _build_params_from_wizard()
    rule_type = st.session_state.get("wizard_type", "threshold")
    if rule_type == "correlation_break" and not str(params.get("benchmark_ticker", "")).strip():
        return "Benchmark ticker is required."
    if rule_type == "custom_expression" and not str(params.get("expression", "")).strip():
        return "Expression is required."
    if rule_type == "missing_data" and int(params.get("min_points", 0)) > int(params.get("lookback_days", 0)):
        return "Minimum points cannot exceed lookback days."
    return None


def _build_params_from_wizard() -> dict:
    rule_type = st.session_state.get("wizard_type", "threshold")
    params: dict = {"dedup_minutes": int(st.session_state.get("wizard_dedup", 60))}
    if st.session_state.get("wizard_aggregation"):
        params["aggregation_key"] = st.session_state.get("wizard_aggregation")
    if rule_type == "threshold":
        params.update({"operator": st.session_state.get("wizard_operator", "<"), "value": float(st.session_state.get("wizard_threshold_value", 0.0))})
    elif rule_type == "z_score":
        params.update({"lookback": int(st.session_state.get("wizard_lookback", 20)), "threshold": float(st.session_state.get("wizard_z_threshold", 2.0))})
    elif rule_type == "volatility":
        params.update({"lookback": int(st.session_state.get("wizard_lookback", 20)), "threshold": float(st.session_state.get("wizard_vol_threshold", 0.03))})
    elif rule_type == "staleness":
        params.update({"max_days": int(st.session_state.get("wizard_max_days", 7))})
    elif rule_type == "missing_data":
        params.update({"lookback_days": int(st.session_state.get("wizard_lookback_days", 30)), "min_points": int(st.session_state.get("wizard_min_points", 25))})
    elif rule_type == "correlation_break":
        params.update({"benchmark_ticker": st.session_state.get("wizard_benchmark", ""), "lookback": int(st.session_state.get("wizard_lookback", 20)), "min_corr": float(st.session_state.get("wizard_min_corr", 0.2))})
    elif rule_type == "custom_expression":
        params.update({"expression": st.session_state.get("wizard_expression", "")})
    return params


def _build_preview_payload() -> dict:
    tickers = [x.strip() for x in st.session_state.get("wizard_scope", "").split(",") if x.strip()]
    return {
        "name": st.session_state.get("wizard_name", ""),
        "rule_type": st.session_state.get("wizard_type", "threshold"),
        "scope": {"tickers": tickers} if tickers else {},
        "params": _build_params_from_wizard(),
        "silence_minutes": int(st.session_state.get("wizard_silence", 0)),
    }


def _submit_wizard_rule(t) -> None:
    svc = AlertsService()
    try:
        err = _validate_wizard_inputs()
        if err:
            st.error(t(err))
            return
        payload_data = _build_preview_payload()
        payload = AlertRuleCreate(
            name=payload_data["name"],
            rule_type=payload_data["rule_type"],
            scope_json=payload_data["scope"],
            params_json=payload_data["params"],
            enabled=True,
            created_by=auth().user_id,
        )
        rule_id = svc.create_rule(actor_id=auth().user_id, payload=payload)
        silence_minutes = int(payload_data["silence_minutes"])
        if silence_minutes > 0:
            svc.set_rule_silenced(rule_id=rule_id, duration_minutes=silence_minutes, actor_id=auth().user_id)
        st.session_state["monitor_rule_wizard_step"] = 1
        push_toast("success", t("Rule created."))
        st.rerun()
    except Exception as e:
        st.error(f"{t('Failed to create rule')}: {e}")


def _render_rules_section(t) -> None:
    st.header(t("Alert Rules"))
    alerts_svc = AlertsService()
    rules = alerts_svc.list_enabled_rules()
    if not rules:
        render_empty_state(t("No alert rules defined."))
        return
    for rule in rules:
        with st.expander(f"{rule.name} — {rule.rule_type}"):
            _render_single_rule(rule, t)


def _render_single_rule(rule: AlertRule, t) -> None:
    alerts_svc = AlertsService()
    st.write(f"📌 **{t('Rule Name')}:** {rule.name}")
    st.write(f"🧩 **{t('Rule Type')}:** {rule.rule_type}")
    st.write(f"⚙️ **{t('Params')}:** {rule.params_json}")
    st.write(f"📍 **{t('Scope')}:** {rule.scope_json}")
    st.write(f"🚦 **{t('Enabled')}:** {rule.enabled}")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button(t("Disable") if rule.enabled else t("Enable"), key=f"toggle_rule_{rule.id}"):
            alerts_svc.set_rule_enabled(rule_id=rule.id, enabled=not rule.enabled, actor_id=auth().user_id)
            push_toast("success", t("Rule updated."))
            st.rerun()
    with col2:
        if st.button(t("Silence Rule"), key=f"silence_rule_{rule.id}"):
            alerts_svc.set_rule_silenced(rule_id=rule.id, duration_minutes=60, actor_id=auth().user_id)
            push_toast("info", t("Rule silenced"))
            st.rerun()
    with col3:
        if st.button(t("Delete Rule"), key=f"del_rule_{rule.id}"):
            alerts_svc.delete_rule(rule_id=rule.id, actor_id=auth().user_id)
            push_toast("warning", t("Rule deleted."))
            st.rerun()


def _render_events_section(t) -> None:
    st.header(t("Recent Alert Events"))
    alerts_svc = AlertsService()
    events = alerts_svc.list_recent_events(limit=100)
    if not events:
        render_empty_state(t("No alert events to display."))
        return
    for ev in events:
        ts = ev.event_ts.strftime("%Y-%m-%d %H:%M:%S")
        with st.container():
            st.write(f"📅 **{t('Time')}:** {ts}  |  📌 **{t('Ticker')}:** {ev.ticker}  |  🧠 **{t('Rule')}:** {ev.rule.name}")
            st.write(f"💬 **{t('Message')}:** {ev.message}")
            if ev.status == AlertEventStatus.NEW:
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button(t("Acknowledge"), key=f"ack_{ev.id}"):
                        _ack_event(ev.id, t)
                with col2:
                    if st.button(t("Notify"), key=f"notify_{ev.id}"):
                        _notify_event(ev, t)
            else:
                st.caption(f"{t('Status')}: {ev.status.value}")


def _run_monitor_cycle(t) -> None:
    task_svc = TaskService()
    try:
        task_svc.queue(
            task_type="alert_monitor_cycle",
            actor_id=auth().user_id,
            celery_signature="quantsentinel.infra.tasks.tasks_monitor.run_alert_monitor",
        )
        render_success_state(t("Monitor cycle started."))
    except Exception as e:
        render_error_state(
            f"{t('Failed to start monitor')}: {e}",
            retry_label=t("Retry"),
            logs_label=t("View Logs"),
            key_prefix="monitor_cycle_error",
        )


def _render_recent_tasks_section(t) -> None:
    st.header(t("Recent Tasks"))
    rows = TaskService().list_recent(limit=10)
    if not rows:
        render_empty_state(t("No tasks to display."))
        return

    for row in rows:
        with st.container(border=True):
            st.write(f"🧩 **{t('Type')}:** {row.task_type}")
            st.write(f"📌 **{t('Status')}:** {row.status.value} | ⏱️ **{t('Progress')}:** {row.progress}%")
            if row.detail:
                st.caption(f"{t('Detail')}: {row.detail}")
            if row.log:
                lines = [ln for ln in row.log.splitlines() if ln.strip()]
                if lines:
                    st.caption(f"{t('Log Summary')}: {lines[-1]}")


def _ack_event(event_id: uuid.UUID, t) -> None:
    try:
        svc = AlertsService()
        svc.ack_event(event_id=event_id, actor_id=auth().user_id)
        push_toast("success", t("Alert acknowledged."))
        st.rerun()
    except Exception as e:
        render_error_state(
            f"{t('Failed to acknowledge')}: {e}",
            retry_label=t("Retry"),
            logs_label=t("View Logs"),
            key_prefix="monitor_ack_error",
        )


def _notify_event(ev: object, t) -> None:
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
            recipients=[ev.ticker],
            channels=["email", "wechat"],
            payload=payload,
            dedup_key=str(ev.id),
            related_entity_type="alert_event",
            related_entity_id=str(ev.id),
        )
        render_success_state(t("Notification queued."))
    except Exception as e:
        render_error_state(
            f"{t('Failed to notify')}: {e}",
            retry_label=t("Retry"),
            logs_label=t("View Logs"),
            key_prefix="monitor_notify_error",
        )
