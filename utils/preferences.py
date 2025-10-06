"""個人化偏好設定工具。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import streamlit as st

PREFERENCE_FILE = Path("data/preferences.json")


def _ensure_pref_file() -> None:
    PREFERENCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not PREFERENCE_FILE.exists():
        PREFERENCE_FILE.write_text("{}", encoding="utf-8")


def load_preferences() -> Dict[str, Any]:
    _ensure_pref_file()
    try:
        return json.loads(PREFERENCE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_preferences(prefs: Dict[str, Any]) -> None:
    _ensure_pref_file()
    PREFERENCE_FILE.write_text(json.dumps(prefs, ensure_ascii=False, indent=2), encoding="utf-8")


def get_user_preference(key: str, default: Any = None) -> Any:
    prefs = st.session_state.setdefault("user_preferences", load_preferences())
    return prefs.get(key, default)


def set_user_preference(key: str, value: Any) -> None:
    prefs = st.session_state.setdefault("user_preferences", load_preferences())
    prefs[key] = value
    save_preferences(prefs)


__all__ = ["get_user_preference", "set_user_preference", "load_preferences", "save_preferences"]
