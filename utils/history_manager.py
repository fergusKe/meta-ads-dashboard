"""Agent 執行歷史管理。"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from utils.logging_manager import log_event

HISTORY_DIR = Path(os.getenv("AGENT_HISTORY_DIR", "data/history"))
HISTORY_FILE = HISTORY_DIR / "agent_history.jsonl"


def _ensure_history_file() -> None:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    if not HISTORY_FILE.exists():
        HISTORY_FILE.touch()


def record_history(agent_name: str, inputs: Dict[str, Any], output: Any, metadata: Dict[str, Any]) -> None:
    """紀錄 Agent 執行歷程。"""
    _ensure_history_file()
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "agent": agent_name,
        "inputs": inputs,
        "output_summary": str(output)[:1000],
        "metadata": metadata,
    }
    with HISTORY_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    log_event("agent_history_recorded", {"agent": agent_name})


def load_history(limit: int = 100) -> List[Dict[str, Any]]:
    """載入最近的歷史紀錄。"""
    if not HISTORY_FILE.exists():
        return []

    records: List[Dict[str, Any]] = []
    with HISTORY_FILE.open("r", encoding="utf-8") as f:
        for line in f.readlines()[-limit:]:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return list(reversed(records))


__all__ = ["record_history", "load_history"]
