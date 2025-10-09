"""即時進度與取消工具。"""

from __future__ import annotations

import hashlib
import inspect
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


def _auto_cancel_key(label: str) -> str:
    caller = inspect.currentframe().f_back  # type: ignore[union-attr]
    identifier = label
    if caller:
        identifier = f"{caller.f_code.co_filename}:{caller.f_lineno}:{label}"
    digest = hashlib.md5(identifier.encode("utf-8")).hexdigest()
    return f"_cancel_btn_{digest}"


def register_cancel_button(label: str = "停止執行", key: str | None = None) -> bool:
    cancel_key = "_agent_cancelled"
    button_key = key or _auto_cancel_key(label)
    if st.button(label, type="secondary", key=button_key):
        st.session_state[cancel_key] = True
    return st.session_state.get(cancel_key, False)


def reset_cancel_flag() -> None:
    st.session_state["_agent_cancelled"] = False


__all__ = ["progress_tracker", "update_progress", "register_cancel_button", "reset_cancel_flag"]
