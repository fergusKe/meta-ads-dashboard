from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd


DEFAULT_HISTORY_PATH = "data/usage/push_history.parquet"

COLUMNS = [
    "timestamp",
    "campaign_id",
    "creative_id",
    "action",
    "channel",
    "status",
    "notes",
]


def _history_path() -> Path:
    path = os.getenv("PUSH_HISTORY_PATH", DEFAULT_HISTORY_PATH)
    return Path(path).expanduser()


def _ensure_dir() -> None:
    path = _history_path()
    path.parent.mkdir(parents=True, exist_ok=True)


def _load() -> pd.DataFrame:
    _ensure_dir()
    path = _history_path()
    if not path.exists():
        return pd.DataFrame(columns=COLUMNS)
    try:
        df = pd.read_parquet(path)
        for column in COLUMNS:
            if column not in df.columns:
                df[column] = None
        return df[COLUMNS]
    except Exception:
        return pd.DataFrame(columns=COLUMNS)


def record(
    campaign_id: str,
    creative_id: str,
    action: str,
    channel: str,
    status: str,
    notes: Optional[str] = None,
) -> pd.DataFrame:
    df = _load()
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "campaign_id": campaign_id,
        "creative_id": creative_id,
        "action": action,
        "channel": channel,
        "status": status,
        "notes": notes or "",
    }
    df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
    df.to_parquet(_history_path(), index=False)
    return df


def load_history(limit: Optional[int] = None) -> pd.DataFrame:
    df = _load().sort_values("timestamp", ascending=False)
    if limit:
        df = df.head(limit)
    return df


def summarize_by_campaign() -> pd.DataFrame:
    df = _load()
    if df.empty:
        return df
    summary = (
        df.groupby("campaign_id")
        .agg(
            pushes=("creative_id", "count"),
            success=("status", lambda s: (s == "sent").sum()),
            pending=("status", lambda s: (s == "pending").sum()),
        )
        .reset_index()
        .sort_values("pushes", ascending=False)
    )
    return summary
