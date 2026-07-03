"""Optional shared-password gate for the Streamlit viewer.

This is opt-in: if no password is configured, the app stays open. Not
every deployment needs auth (e.g. running purely on localhost for
yourself), so we don't force friction on users who haven't set one up.
"""

import streamlit as st


def _configured_password() -> str | None:
    """Read the shared password from Streamlit secrets, if any is set.

    Wrapped in a try/except because st.secrets raises if no secrets.toml
    file exists at all, which is the expected state for anyone who hasn't
    opted into auth.
    """
    try:
        return st.secrets.get("app_password")
    except Exception:
        return None


def require_password() -> bool:
    """Render a login gate if a password is configured.

    Returns True once the visitor is allowed through (either no password
    is set, or the correct one has been entered this session).
    """
    configured_password = _configured_password()
    if not configured_password:
        return True

    if st.session_state.get("authenticated"):
        return True

    st.title("Project Gallery")
    entered = st.text_input("Password", type="password")
    if st.button("Enter"):
        if entered == configured_password:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    return False
