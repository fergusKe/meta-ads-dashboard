from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

import pandas as pd
from dotenv import load_dotenv

from . import template_store


load_dotenv()

LOG_COLUMNS = [
    "template_id",
    "name",
    "status",
    "reviewer",
    "outcome",
    "notes",
    "recorded_at",
    "metadata",
]


def _log_path() -> Path:
    path = os.getenv("TEMPLATE_REVIEW_LOG_PATH", "data/templates/review_logs.parquet")
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


def _prepare_metadata(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    prepared = df.copy()
    prepared["created_at"] = pd.to_datetime(prepared.get("created_at"), errors="coerce")
    prepared["updated_at"] = pd.to_datetime(prepared.get("updated_at"), errors="coerce")
    prepared["last_reviewed_at"] = pd.to_datetime(prepared.get("last_reviewed_at"), errors="coerce")
    return prepared


def generate_schedule(
    cycle_days: int = 14,
    reference_date: datetime | None = None,
    template_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    df = template_df if template_df is not None else template_store.load_metadata()
    if df.empty:
        return pd.DataFrame(columns=[
            "template_id",
            "name",
            "status",
            "days_since_review",
            "next_review_date",
            "priority",
        ])

    reference = reference_date or datetime.utcnow()
    prepared = _prepare_metadata(df)
    prepared["last_review"] = prepared["last_reviewed_at"].fillna(prepared["updated_at"]).fillna(prepared["created_at"])
    prepared["last_review"] = prepared["last_review"].fillna(pd.Timestamp(reference))

    prepared["days_since_review"] = (reference - prepared["last_review"]).dt.days.clip(lower=0)
    prepared["next_review_date"] = prepared["last_review"] + pd.to_timedelta(cycle_days, unit="D")

    def _score(row: pd.Series) -> int:
        if row.get("status") not in {"approved"}:
            return 0
        if row["days_since_review"] >= cycle_days * 2:
            return 1
        if row["days_since_review"] >= cycle_days:
            return 2
        return 3

    prepared["priority_score"] = prepared.apply(_score, axis=1)
    priority_map = {0: "高", 1: "高", 2: "中", 3: "低"}
    prepared["priority"] = prepared["priority_score"].map(priority_map).fillna("低")

    schedule = prepared[[
        "template_id",
        "name",
        "status",
        "days_since_review",
        "next_review_date",
        "priority",
    ]].copy()
    schedule["priority_score"] = prepared["priority_score"]
    schedule.sort_values(
        by=["priority_score", "days_since_review"],
        ascending=[True, False],
        inplace=True,
    )
    schedule.drop(columns=["priority_score"], inplace=True)
    schedule["next_review_date"] = schedule["next_review_date"].dt.strftime("%Y-%m-%d")
    return schedule.reset_index(drop=True)


def record_review(
    template_id: str,
    reviewer: str,
    outcome: str,
    notes: str = "",
    status: str | None = None,
    metadata: Dict[str, Any] | None = None,
) -> pd.DataFrame:
    template = template_store.load_metadata()
    row = template[template["template_id"] == template_id]
    if row.empty:
        raise ValueError(f"找不到模板 {template_id}")
    name = row.iloc[0]["name"]
    current_status = status or row.iloc[0]["status"]

    template_store.mark_status(template_id=template_id, status=current_status, reviewer=reviewer, notes=notes)

    logs = _load_logs()
    entry = {
        "template_id": template_id,
        "name": name,
        "status": current_status,
        "reviewer": reviewer,
        "outcome": outcome,
        "notes": notes,
        "recorded_at": datetime.utcnow().isoformat(),
        "metadata": json.dumps(metadata or {}, ensure_ascii=False),
    }
    logs = pd.concat([logs, pd.DataFrame([entry], columns=LOG_COLUMNS)], ignore_index=True)
    _save_logs(logs)
    return logs


def load_review_logs(template_id: str | None = None) -> pd.DataFrame:
    logs = _load_logs()
    if template_id:
        logs = logs[logs["template_id"] == template_id]
    return logs.sort_values("recorded_at", ascending=False).reset_index(drop=True)
