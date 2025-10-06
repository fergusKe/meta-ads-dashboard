"""即時進度與取消工具。"""

from __future__ import annotations

import streamlit as st
from contextlib import contextmanager
from typing import Iterator


@contextmanager
def progress_tracker(total_steps: int, label: str = "處理中...") -> Iterator[None]:
    progress = st.progress(0.0, text=label)
    current = 0

    def update(step: int = 1, text: str | None = None) -> None:
        nonlocal current
        current += step
        ratio = min(current / max(total_steps, 1), 1.0)
        progress.progress(ratio, text=text or label)

    st.session_state["_progress_update"] = update
    try:
        yield
    finally:
        progress.empty()
        st.session_state.pop("_progress_update", None)


def update_progress(step: int = 1, text: str | None = None) -> None:
    updater = st.session_state.get("_progress_update")
    if callable(updater):
        updater(step, text)


def register_cancel_button(label: str = "停止執行") -> bool:
    cancel_key = "_agent_cancelled"
    if st.button(label, type="secondary"):
        st.session_state[cancel_key] = True
    return st.session_state.get(cancel_key, False)


def reset_cancel_flag() -> None:
    st.session_state["_agent_cancelled"] = False


__all__ = ["progress_tracker", "update_progress", "register_cancel_button", "reset_cancel_flag"]
