"""Shared UI feedback utilities for Streamlit pages."""

from __future__ import annotations

import streamlit as st


def queue_completion_message(key: str, message: str, toast: bool = True) -> None:
    """Store a completion message to display on the next render cycle."""
    state_key = f"_completion_msg_{key}"
    toast_key = f"_completion_toast_{key}"
    st.session_state[state_key] = message
    st.session_state[toast_key] = toast


def render_completion_message(key: str) -> None:
    """Render and clear a queued completion message."""
    state_key = f"_completion_msg_{key}"
    toast_key = f"_completion_toast_{key}"
    message = st.session_state.pop(state_key, None)
    if not message:
        return

    st.success(message)
    if st.session_state.pop(toast_key, False):
        try:
            st.toast(message, icon="✅")
        except Exception:
            # Older Streamlit versions may not support toast; ignore silently.
            pass


__all__ = ["queue_completion_message", "render_completion_message"]
