"""API Key 輪替與配額管理工具。"""

from __future__ import annotations

import os
from collections import deque
from dataclasses import dataclass
from threading import Lock
from typing import Deque, Optional

from utils.logging_manager import log_event, log_exception


@dataclass
class APIKeyStatus:
    """追蹤單一 API key 的使用狀態。"""

    key: str
    failed_attempts: int = 0
    disabled: bool = False


class APIKeyManager:
    """管理多組 API Key，支援輪替與故障隔離。"""

    def __init__(self) -> None:
        keys_env = os.getenv("OPENAI_API_KEYS") or os.getenv("OPENAI_API_KEY", "")
        keys = [k.strip() for k in keys_env.split(",") if k.strip()]

        if not keys:
            self._queue: Deque[APIKeyStatus] = deque()
        else:
            self._queue = deque(APIKeyStatus(key=k) for k in keys)

        self._lock = Lock()

    def has_keys(self) -> bool:
        return bool(self._queue)

    def acquire(self) -> Optional[str]:
        """取得下一組可用的 API Key。"""
        with self._lock:
            if not self._queue:
                return None

            # 轉圈直到找到可用的 key 或回到起點
            for _ in range(len(self._queue)):
                status = self._queue[0]
                if not status.disabled:
                    self._queue.rotate(-1)
                    log_event("api_key_acquired", {"key_suffix": status.key[-4:]})
                    return status.key
                self._queue.rotate(-1)

            # 全部被標註為 disabled
            return None

    def report_success(self, key: str) -> None:
        with self._lock:
            for status in self._queue:
                if status.key == key:
                    status.failed_attempts = 0
                    break

    def report_failure(self, key: str) -> None:
        with self._lock:
            for status in self._queue:
                if status.key == key:
                    status.failed_attempts += 1
                    log_event("api_key_failure", {"key_suffix": key[-4:], "fails": status.failed_attempts})
                    if status.failed_attempts >= int(os.getenv("API_KEY_MAX_FAILURE", "3")):
                        status.disabled = True
                        log_event("api_key_disabled", {"key_suffix": key[-4:]})
                    break

    def reset(self) -> None:
        with self._lock:
            for status in self._queue:
                status.failed_attempts = 0
                status.disabled = False


_key_manager: Optional[APIKeyManager] = None


def get_api_key_manager() -> APIKeyManager:
    global _key_manager
    if _key_manager is None:
        try:
            _key_manager = APIKeyManager()
        except Exception as exc:
            log_exception(exc, "init_api_key_manager")
            _key_manager = APIKeyManager()
    return _key_manager


__all__ = ["APIKeyManager", "get_api_key_manager"]
