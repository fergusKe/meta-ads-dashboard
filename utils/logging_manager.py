"""
統一日誌與監控系統。

- 以 `logging` 標準庫集中管理各模組輸出的紀錄。
- 預設輸出至 `logs/ai_agents.log`，亦可透過環境變數調整路徑與等級。
- 提供便捷函式記錄事件、指標與例外狀況。
- 與 Streamlit/CLI 共用，確保本地與部署環境一致。
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional

import streamlit as st

DEFAULT_LOG_FILE = os.getenv("AGENT_LOG_FILE", "logs/ai_agents.log")
DEFAULT_LOG_LEVEL = os.getenv("AGENT_LOG_LEVEL", "INFO").upper()
DEFAULT_MAX_BYTES = int(os.getenv("AGENT_LOG_MAX_BYTES", 5 * 1024 * 1024))
DEFAULT_BACKUP_COUNT = int(os.getenv("AGENT_LOG_BACKUP_COUNT", 3))

_LOGGER_CACHE: Dict[str, logging.Logger] = {}


def _ensure_log_directory(path: str) -> None:
    """確保日誌目錄存在。"""
    log_path = Path(path).expanduser()
    log_path.parent.mkdir(parents=True, exist_ok=True)


def get_logger(name: str = "meta_ads") -> logging.Logger:
    """取得或建立指定名稱的 logger。"""
    if name in _LOGGER_CACHE:
        return _LOGGER_CACHE[name]

    _ensure_log_directory(DEFAULT_LOG_FILE)

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, DEFAULT_LOG_LEVEL, logging.INFO))

    if not logger.handlers:
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # 旋轉檔案 handler
        file_handler = RotatingFileHandler(
            DEFAULT_LOG_FILE,
            maxBytes=DEFAULT_MAX_BYTES,
            backupCount=DEFAULT_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Streamlit / CLI console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    _LOGGER_CACHE[name] = logger
    return logger


def log_event(event: str, details: Optional[Dict[str, Any]] = None, level: int = logging.INFO) -> None:
    """
    記錄一般事件。

    Args:
        event: 事件名稱
        details: 事件補充資訊
        level: logging 等級
    """
    logger = get_logger()
    payload = {"event": event, **(details or {})}
    logger.log(level, json.dumps(payload, ensure_ascii=False))

    # 提供給 Streamlit 顯示（選擇性）
    if os.getenv("AGENT_LOG_TO_STREAMLIT", "false").lower() == "true":
        st.caption(f"📋 日誌：{event} - {payload}")


def log_exception(error: Exception, context: Optional[str] = None) -> None:
    """記錄例外狀況並附上堆疊。"""
    logger = get_logger()
    message = context or "Agent Exception"
    logger.exception("%s | %s", message, str(error))


def log_metric(name: str, value: Any, namespace: str = "agent") -> None:
    """記錄數值型指標（成本、延遲等）。"""
    logger = get_logger()
    payload = {
        "metric": name,
        "namespace": namespace,
        "value": value,
        "timestamp": datetime.utcnow().isoformat(),
    }
    logger.info(json.dumps(payload, ensure_ascii=False))


__all__ = ["get_logger", "log_event", "log_exception", "log_metric"]
