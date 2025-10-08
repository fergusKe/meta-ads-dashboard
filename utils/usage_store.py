from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import pandas as pd


DEFAULT_USAGE_PATH = "data/usage/events.parquet"

EVENT_COLUMNS = [
    "feature",
    "event_type",
    "timestamp",
    "metadata",
]


def _event_path() -> Path:
    path = os.getenv("FEATURE_USAGE_EVENT_PATH", DEFAULT_USAGE_PATH)
    return Path(path).expanduser()


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


def record_event(feature: str, event_type: str, metadata: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    df = _load_events()
    entry = {
        "feature": feature,
        "event_type": event_type,
        "timestamp": datetime.utcnow().isoformat(),
        "metadata": json.dumps(metadata or {}, ensure_ascii=False),
    }
    df = pd.concat([df, pd.DataFrame([entry], columns=EVENT_COLUMNS)], ignore_index=True)
    df.to_parquet(_event_path(), index=False)
    return df


def _parse_metadata(series: pd.Series) -> pd.Series:
    def _try_parse(value: Any) -> Any:
        if isinstance(value, dict):
            return value
        if isinstance(value, str) and value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value

    return series.apply(_try_parse)


def load_events(
    feature: str | None = None,
    limit: int | None = None,
    parse_metadata: bool = False,
    preprocess: Optional[Callable[[pd.DataFrame], pd.DataFrame]] = None,
) -> pd.DataFrame:
    df = _load_events()
    if feature:
        df = df[df["feature"] == feature]
    df = df.sort_values("timestamp", ascending=False)
    if parse_metadata:
        df = df.copy()
        df["metadata"] = _parse_metadata(df["metadata"])
    if preprocess:
        df = preprocess(df)
    if limit:
        df = df.head(limit)
    return df


def summarize_events(feature: str | None = None) -> pd.DataFrame:
    df = _load_events()
    if feature:
        df = df[df["feature"] == feature]
    if df.empty:
        return df
    summary = (
        df.groupby(["feature", "event_type"])
        .size()
        .reset_index(name="count")
        .pivot(index="feature", columns="event_type", values="count")
        .fillna(0)
        .reset_index()
    )
    return summary


def summarize_daily(feature: str | None = None, event_type: str | None = None) -> pd.DataFrame:
    df = _load_events()
    if feature:
        df = df[df["feature"] == feature]
    if event_type:
        df = df[df["event_type"] == event_type]
    if df.empty:
        return df
    df = df.copy()
    df["date"] = pd.to_datetime(df["timestamp"]).dt.date
    summary = (
        df.groupby(["date", "event_type"])
        .size()
        .reset_index(name="count")
        .sort_values("date", ascending=True)
    )
    return summary


def top_metadata_entries(feature: str, key: str, limit: int = 5) -> pd.DataFrame:
    df = load_events(feature=feature, parse_metadata=True)
    if df.empty:
        return df
    df = df[df["metadata"].apply(lambda x: isinstance(x, dict) and key in x)]
    if df.empty:
        return df
    values = df["metadata"].apply(lambda x: x.get(key))
    counts = values.value_counts().reset_index()
    counts.columns = [key, "count"]
    counts = counts.head(limit)
    return counts
