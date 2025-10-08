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
    "license_id",
    "brand_code",
    "status",
    "metrics",
    "notes",
    "recorded_by",
    "recorded_at",
]


def _log_path() -> Path:
    path = os.getenv("LICENSE_PILOT_LOG_PATH", "data/licenses/pilot_logs.parquet")
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


def log_pilot_event(
    license_id: str,
    brand_code: str,
    status: str,
    metrics: Dict[str, Any] | None = None,
    notes: str = "",
    recorded_by: str = "",
) -> pd.DataFrame:
    df = _load_logs()
    entry = {
        "pilot_id": f"pilot_{uuid.uuid4().hex[:10]}",
        "license_id": license_id,
        "brand_code": brand_code,
        "status": status,
        "metrics": json.dumps(metrics or {}, ensure_ascii=False),
        "notes": notes,
        "recorded_by": recorded_by,
        "recorded_at": datetime.utcnow().isoformat(),
    }
    df = pd.concat([df, pd.DataFrame([entry], columns=LOG_COLUMNS)], ignore_index=True)
    _save_logs(df)
    return df


def load_pilot_logs(license_id: str | None = None, brand_code: str | None = None) -> pd.DataFrame:
    df = _load_logs()
    if license_id:
        df = df[df["license_id"] == license_id]
    if brand_code:
        df = df[df["brand_code"] == brand_code]
    return df.reset_index(drop=True)


def summarize_pilots(license_id: str | None = None) -> pd.DataFrame:
    df = load_pilot_logs(license_id=license_id)
    if df.empty:
        return df
    parsed = df.copy()
    parsed["metrics"] = parsed["metrics"].apply(lambda value: json.loads(value) if isinstance(value, str) and value else {})
    summary_rows = []
    for (lic_id, brand_code), group in parsed.groupby(["license_id", "brand_code"]):
        total = len(group)
        latest = group.sort_values("recorded_at", ascending=False).iloc[0]
        success = int((group["status"] == "success").sum())
        fail = int((group["status"] == "fail").sum())
        summary_rows.append(
            {
                "license_id": lic_id,
                "brand_code": brand_code,
                "total_updates": total,
                "success": success,
                "fail": fail,
                "latest_status": latest["status"],
                "latest_metrics": latest["metrics"],
                "last_update": latest["recorded_at"],
            }
        )
    return pd.DataFrame(summary_rows)
