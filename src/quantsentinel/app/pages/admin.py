from __future__ import annotations

import uuid
from typing import Optional

import streamlit as st

from quantsentinel.app.ui.state import auth, push_toast
from quantsentinel.i18n.gettext import get_translator
from quantsentinel.services.auth_service import AuthService, LoginResult
from quantsentinel.infra.db.models import UserRole
from quantsentinel.services.user_service import UserService
from quantsentinel.services.audit_service import AuditService


def render() -> None:
    """
    Admin page: user management + audit log viewer.
    Access controlled to Admin role only.
    """
    a = auth()
    t = get_translator(a.language)

    # RBAC guard
    if a.role != UserRole.ADMIN:
        st.error(t("Access denied — admin only."))
        return

    st.markdown(f"## {t('Admin Console')}")

    st.sidebar.markdown(f"### {t('Admin Controls')}")

    section = st.sidebar.radio(
        label=t("Select section"),
        options=[t("Users"), t("Audit Logs")],
        index=0,
    )

    if section == t("Users"):
        _render_user_management(t)
    else:
        _render_audit_logs(t)


# -----------------------------------
# USER MANAGEMENT
# -----------------------------------

def _render_user_management(t) -> None:
    st.markdown(f"### {t('Manage Users')}")

    svc = UserService()
    current_user_id = auth().user_id

    # LIST USERS
    st.subheader(t("User List"))
    users = svc.list_users()
    for user in users:
        with st.expander(f"{user.username} ({user.role.value})"):
            col1, col2 = st.columns([2, 3])
            with col1:
                st.write(f"**{t('Username')}:** {user.username}")
                st.write(f"**{t('Email')}:** {user.email}")
                st.write(f"**{t('Role')}:** {user.role.value}")
                st.write(f"**{t('Active')}:** {user.is_active}")
            with col2:
                st.write(f"**{t('Default Language')}:** {user.default_language}")

            if st.button(t("Deactivate") if user.is_active else t("Activate"), key=f"toggle_{user.id}"):
                svc.set_active(user_id=user.id, is_active=not user.is_active)
                push_toast("success", t("User updated."))
                st.experimental_rerun()

            new_role = st.selectbox(
                t("Change role"), options=[r.value for r in UserRole], index=list(UserRole).index(user.role), key=f"role_{user.id}"
            )
            if new_role != user.role.value:
                svc.set_role(user_id=user.id, role=UserRole(new_role))
                push_toast("success", t("Role updated."))
                st.experimental_rerun()

            if st.button(t("Reset password to default"), key=f"reset_{user.id}"):
                svc.reset_password(user_id=user.id, new_password="changeme123")
                push_toast("warning", t("Password reset — force user to change."))

    st.divider()

    # CREATE NEW USER FORM
    st.subheader(t("Create New User"))
    with st.form(key="create_user_form"):
        new_username = st.text_input(t("Username"))
        new_email = st.text_input(t("Email"))
        new_password = st.text_input(t("Password"), type="password")
        new_role = st.selectbox(t("Role"), options=[r.value for r in UserRole])
        create_submitted = st.form_submit_button(t("Create"))

    if create_submitted:
        if not new_username or not new_password:
            st.error(t("Username and password are required"))
        else:
            svc.create_user(username=new_username, email=new_email, password=new_password, role=UserRole(new_role))
            push_toast("success", t("User created."))
            st.experimental_rerun()


# -----------------------------------
# AUDIT LOG VIEWER
# -----------------------------------

def _render_audit_logs(t) -> None:
    st.markdown(f"### {t('Audit Logs')}")

    svc = AuditService()

    search_user = st.text_input(t("Filter by user"))
    search_action = st.text_input(t("Filter by action"))

    logs = svc.get_recent(limit=300)
    if search_user:
        logs = [l for l in logs if search_user.lower() in (l.actor_username or "").lower()]
    if search_action:
        logs = [l for l in logs if search_action.lower() in l.action.lower()]

    for entry in logs:
        st.write(f"[{entry.ts}] {entry.actor_username or '-'} {entry.action} {entry.entity_type} ({entry.entity_id})")
        st.caption(entry.payload_json)