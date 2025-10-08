from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, List, Dict, Any, Sequence

import pandas as pd
from dotenv import load_dotenv

from . import brand_license_store


load_dotenv()

PLAN_COLUMNS = [
    "license_id",
    "brand_code",
    "license_name",
    "brand",
    "channel",
    "recipient",
    "send_on",
    "days_until_expiry",
    "message",
]

LOG_COLUMNS = PLAN_COLUMNS + ["status", "dispatched_at", "metadata"]


def _log_path() -> Path:
    path = os.getenv("LICENSE_NOTIFICATION_LOG_PATH", "data/licenses/notifications.parquet")
    return Path(path).expanduser()


def _ensure_log_dir() -> None:
    path = _log_path()
    path.parent.mkdir(parents=True, exist_ok=True)


def _load_log() -> pd.DataFrame:
    _ensure_log_dir()
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


def _save_log(df: pd.DataFrame) -> None:
    _ensure_log_dir()
    df.to_parquet(_log_path(), index=False)


def _parse_json(value: Any) -> Dict[str, Any]:
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _parse_applied_brands(value: Any) -> List[Dict[str, Any]]:
    if not value:
        return []
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [item for item in parsed if isinstance(item, dict)]
        except json.JSONDecodeError:
            return []
    return []


def _extract_expiration(candidate: Dict[str, Any], fallback: Dict[str, Any]) -> datetime | None:
    keys = ["expires_at", "expiration_date", "end_date", "contract_end"]
    for key in keys:
        value = candidate.get(key) or fallback.get(key)
        if not value:
            continue
        try:
            ts = pd.to_datetime(value, errors="coerce")
            if pd.notna(ts):
                return ts.to_pydatetime()
        except Exception:
            continue
    duration_days = candidate.get("duration_days") or fallback.get("duration_days")
    applied_at = candidate.get("applied_at") or fallback.get("applied_at")
    if duration_days and applied_at:
        base = pd.to_datetime(applied_at, errors="coerce")
        if pd.notna(base):
            try:
                days = int(duration_days)
            except (TypeError, ValueError):
                days = None
            if days is not None:
                return (base + pd.Timedelta(days=days)).to_pydatetime()
    return None


def _resolve_contacts(candidate: Dict[str, Any], fallback: Dict[str, Any]) -> List[Dict[str, str]]:
    contacts: List[Dict[str, str]] = []

    def _append(raw: Any) -> None:
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    channel = item.get("channel") or "email"
                    target = item.get("target") or item.get("recipient")
                    if target:
                        contacts.append({"channel": channel, "recipient": target})
                elif isinstance(item, str):
                    contacts.append({"channel": "email", "recipient": item})
        elif isinstance(raw, str) and raw:
            contacts.append({"channel": "email", "recipient": raw})

    _append(candidate.get("contacts"))
    _append(fallback.get("contacts"))

    email = candidate.get("contact_email") or fallback.get("contact_email")
    if email:
        contacts.append({"channel": "email", "recipient": email})

    unique: Dict[tuple[str, str], Dict[str, str]] = {}
    for item in contacts:
        channel = item.get("channel") or "email"
        recipient = item.get("recipient")
        if not recipient:
            continue
        unique[(channel, recipient)] = {"channel": channel, "recipient": recipient}
    return list(unique.values())


def _build_message(row: Dict[str, Any], expiry: datetime, days_left: int) -> str:
    license_name = row.get("name", "")
    brand = row.get("brand", "")
    return (
        f"授權方案【{license_name}】針對品牌 {brand} 將於 {expiry.strftime('%Y-%m-%d')} 到期 "
        f"(尚餘 {days_left} 天)，請儘速確認續約或調整知識庫。"
    )


def build_notification_plan(
    within_days: int = 14,
    reference_date: datetime | None = None,
    channels: Iterable[str] | None = None,
) -> pd.DataFrame:
    metadata = brand_license_store.load_metadata()
    if metadata.empty:
        return pd.DataFrame(columns=PLAN_COLUMNS)

    reference = reference_date or datetime.utcnow()
    allowed_channels = {channel for channel in (channels or ["email", "slack"])}
    plans: List[Dict[str, Any]] = []

    for _, row in metadata.iterrows():
        extra = _parse_json(row.get("extra"))
        applied_brands = _parse_applied_brands(row.get("applied_brands"))
        if not applied_brands:
            continue

        for item in applied_brands:
            expiry = _extract_expiration(item, extra)
            if not expiry:
                continue
            days_left = (expiry.date() - reference.date()).days
            if days_left < 0 or days_left > within_days:
                continue
            contacts = _resolve_contacts(item, extra)
            for contact in contacts:
                channel = contact.get("channel") or "email"
                if channel not in allowed_channels:
                    continue
                plan_entry = {
                    "license_id": row.get("license_id"),
                    "brand_code": item.get("brand_code") or "",
                    "license_name": row.get("name"),
                    "brand": row.get("brand"),
                    "channel": channel,
                    "recipient": contact.get("recipient"),
                    "send_on": (expiry - timedelta(days=min(days_left, 3))).strftime("%Y-%m-%d"),
                    "days_until_expiry": days_left,
                    "message": _build_message(row, expiry, days_left),
                }
                plans.append(plan_entry)

    if not plans:
        return pd.DataFrame(columns=PLAN_COLUMNS)
    result = pd.DataFrame(plans, columns=PLAN_COLUMNS)
    result.sort_values(["days_until_expiry", "brand_code"], inplace=True)
    return result.reset_index(drop=True)


def record_notifications(plan: pd.DataFrame, status: str = "scheduled", metadata: Dict[str, Any] | None = None) -> pd.DataFrame:
    if plan.empty:
        return _load_log()

    log_df = _load_log()
    timestamp = datetime.utcnow().isoformat()
    entries = plan.copy()
    entries["status"] = status
    entries["dispatched_at"] = timestamp if status == "sent" else None
    entries["metadata"] = json.dumps(metadata or {}, ensure_ascii=False)

    combined = pd.concat([log_df, entries], ignore_index=True)
    _save_log(combined)
    return combined


def load_notification_log() -> pd.DataFrame:
    return _load_log()


def pending_notifications(reference_date: datetime | None = None) -> pd.DataFrame:
    log_df = _load_log()
    if log_df.empty:
        return log_df
    reference = reference_date or datetime.utcnow()
    mask = (log_df["status"] == "scheduled") & (pd.to_datetime(log_df["send_on"]) <= reference)
    return log_df[mask].reset_index(drop=True)
