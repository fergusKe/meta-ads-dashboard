from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

import pandas as pd
from dotenv import load_dotenv


load_dotenv()

DEFAULT_EVENT_PATH = "data/templates/events.parquet"

EVENT_COLUMNS = [
    "template_id",
    "event_type",
    "timestamp",
    "metadata",
]


def _event_path() -> Path:
    return Path(os.getenv("TEMPLATE_EVENT_PATH", DEFAULT_EVENT_PATH)).expanduser()


def _ensure_dir() -> None:
    path = _event_path()
    path.parent.mkdir(parents=True, exist_ok=True)


def _load_events() -> pd.DataFrame:
    _ensure_dir()
    path = _event_path()
    if not path.exists():
        return pd.DataFrame(columns=EVENT_COLUMNS)
    try:
        df = pd.read_parquet(path)
        for column in EVENT_COLUMNS:
            if column not in df.columns:
                df[column] = None
        return df[EVENT_COLUMNS]
    except Exception:
        return pd.DataFrame(columns=EVENT_COLUMNS)


def record_event(template_id: str, event_type: str, metadata: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    df = _load_events()
    entry = {
        "template_id": template_id,
        "event_type": event_type,
        "timestamp": datetime.utcnow().isoformat(),
        "metadata": json.dumps(metadata or {}, ensure_ascii=False),
    }
    df = pd.concat([df, pd.DataFrame([entry], columns=EVENT_COLUMNS)], ignore_index=True)
    df.to_parquet(_event_path(), index=False)
    return df


def load_events(template_id: str | None = None, event_type: str | None = None, limit: int | None = None) -> pd.DataFrame:
    df = _load_events()
    if template_id:
        df = df[df["template_id"] == template_id]
    if event_type:
        df = df[df["event_type"] == event_type]
    df = df.sort_values("timestamp", ascending=False)
    if limit:
        df = df.head(limit)
    return df


def summarize_events() -> pd.DataFrame:
    df = _load_events()
    if df.empty:
        return df
    summary = (
        df.groupby(["template_id", "event_type"])
        .size()
        .reset_index(name="count")
        .pivot(index="template_id", columns="event_type", values="count")
        .fillna(0)
        .reset_index()
    )
    return summary


def _parse_metadata(value: Any) -> Dict[str, Any]:
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {"raw": value}
    return {"raw": value}


def load_feedback(template_id: str | None = None, limit: int | None = None) -> pd.DataFrame:
    df = _load_events()
    if df.empty:
        return df
    df = df[df["event_type"] == "feedback"]
    if template_id:
        df = df[df["template_id"] == template_id]
    df = df.sort_values("timestamp", ascending=False)
    if limit:
        df = df.head(limit)
    parsed = df.copy()
    parsed["metadata"] = parsed["metadata"].apply(_parse_metadata)
    parsed["rating"] = parsed["metadata"].apply(lambda meta: meta.get("rating"))
    parsed["comment"] = parsed["metadata"].apply(lambda meta: meta.get("comment", ""))
    parsed["contact"] = parsed["metadata"].apply(lambda meta: meta.get("contact", ""))
    return parsed[["template_id", "rating", "comment", "contact", "timestamp", "metadata"]].reset_index(drop=True)


def summarize_feedback(template_id: str | None = None) -> pd.DataFrame:
    feedback = load_feedback(template_id=template_id)
    if feedback.empty:
        return feedback
    stats = (
        feedback.groupby("template_id")
        .agg(
            feedback_count=("rating", "count"),
            avg_rating=("rating", "mean"),
        )
        .reset_index()
    )
    stats["avg_rating"] = stats["avg_rating"].round(2)
    return stats
