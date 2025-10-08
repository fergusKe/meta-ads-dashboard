from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import pandas as pd
from dotenv import load_dotenv


load_dotenv()

LOG_COLUMNS = [
    "pilot_id",
    "creative_id",
    "campaign_id",
    "action_taken",
    "outcome",
    "metrics",
    "notes",
    "recorded_by",
    "recorded_at",
]


def _log_path() -> Path:
    path = os.getenv("FATIGUE_PILOT_LOG_PATH", "data/fatigue/pilot_logs.parquet")
    return Path(path).expanduser()


def _ensure_dir() -> None:
    path = _log_path()
    path.parent.mkdir(parents=True, exist_ok=True)


def _load_logs() -> pd.DataFrame:
    _ensure_dir()
    path = _log_path()
    if not path.exists():
        return pd.DataFrame(columns=LOG_COLUMNS)
    try:
        df = pd.read_parquet(path)
        for column in LOG_COLUMNS:
            if column not in df.columns:
                df[column] = None
        return df[LOG_COLUMNS]
    except Exception:
        return pd.DataFrame(columns=LOG_COLUMNS)


def _save_logs(df: pd.DataFrame) -> None:
    _ensure_dir()
    df.to_parquet(_log_path(), index=False)


def log_pilot_result(
    creative_id: str,
    campaign_id: str,
    action_taken: str,
    outcome: str,
    metrics: Dict[str, Any] | None = None,
    notes: str = "",
    recorded_by: str = "",
) -> pd.DataFrame:
    df = _load_logs()
    entry = {
        "pilot_id": f"fatigue_{uuid.uuid4().hex[:10]}",
        "creative_id": creative_id,
        "campaign_id": campaign_id,
        "action_taken": action_taken,
        "outcome": outcome,
        "metrics": json.dumps(metrics or {}, ensure_ascii=False),
        "notes": notes,
        "recorded_by": recorded_by,
        "recorded_at": datetime.utcnow().isoformat(),
    }
    df = pd.concat([df, pd.DataFrame([entry], columns=LOG_COLUMNS)], ignore_index=True)
    _save_logs(df)
    return df


def load_pilot_results(campaign_id: str | None = None) -> pd.DataFrame:
    df = _load_logs()
    if campaign_id:
        df = df[df["campaign_id"] == campaign_id]
    return df.reset_index(drop=True)


def summarize_results() -> pd.DataFrame:
    df = _load_logs()
    if df.empty:
        return df
    parsed = df.copy()
    parsed["metrics"] = parsed["metrics"].apply(lambda value: json.loads(value) if isinstance(value, str) and value else {})

    summary_rows = []
    for (campaign_id, creative_id), group in parsed.groupby(["campaign_id", "creative_id"]):
        latest = group.sort_values("recorded_at", ascending=False).iloc[0]
        success_rate = None
        if "lift" in latest["metrics"]:
            success_rate = latest["metrics"]["lift"]
        summary_rows.append(
            {
                "campaign_id": campaign_id,
                "creative_id": creative_id,
                "total_updates": len(group),
                "last_outcome": latest["outcome"],
                "last_action": latest["action_taken"],
                "last_metrics": latest["metrics"],
                "last_update": latest["recorded_at"],
                "success_indicator": success_rate,
            }
        )
    return pd.DataFrame(summary_rows)
