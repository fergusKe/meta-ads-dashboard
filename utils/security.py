"""敏感資料處理工具。"""

from __future__ import annotations

import re
from typing import Any, Dict

SENSITIVE_PATTERNS = [
    re.compile(r"\b\d{4}-\d{4}-\d{4}-\d{4}\b"),  # 卡號
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
]


def mask_sensitive(text: str) -> str:
    masked = text
    for pattern in SENSITIVE_PATTERNS:
        masked = pattern.sub("***", masked)
    return masked


def sanitize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    sanitized: Dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, str):
            sanitized[key] = mask_sensitive(value)
        else:
            sanitized[key] = value
    return sanitized


__all__ = ["mask_sensitive", "sanitize_payload"]
