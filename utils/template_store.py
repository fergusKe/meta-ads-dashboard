from __future__ import annotations

import json
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Iterable, Mapping, Dict, Any

import pandas as pd
from dotenv import load_dotenv


load_dotenv()

DEFAULT_METADATA_PATH = "data/templates/metadata.parquet"
DEFAULT_STORAGE_DIR = "assets/templates"
AUDIT_LOG_PATH = "data/templates/audit_logs.parquet"

AUDIT_COLUMNS = [
    "template_id",
    "timestamp",
    "status",
    "reviewer",
    "notes",
    "checks",
]

SCHEMA = [
    "template_id",
    "name",
    "category",
    "format",
    "description",
    "tags",
    "version",
    "status",
    "license_type",
    "price_type",
    "price",
    "storage_path",
    "thumbnail_path",
    "author",
    "reviewer",
    "created_at",
    "updated_at",
    "last_reviewed_at",
    "extra",
]


def _metadata_path() -> Path:
    path = os.getenv("TEMPLATE_METADATA_PATH", DEFAULT_METADATA_PATH)
    return Path(path).expanduser()


def _storage_dir() -> Path:
    path = os.getenv("TEMPLATE_STORAGE_DIR", DEFAULT_STORAGE_DIR)
    return Path(path).expanduser()


def _audit_path() -> Path:
    return Path(os.getenv("TEMPLATE_AUDIT_LOG_PATH", AUDIT_LOG_PATH)).expanduser()


def _ensure_dirs() -> None:
    meta_path = _metadata_path()
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path = _storage_dir()
    storage_path.mkdir(parents=True, exist_ok=True)
    audit_path = _audit_path()
    audit_path.parent.mkdir(parents=True, exist_ok=True)


def _empty_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=SCHEMA)


def load_metadata() -> pd.DataFrame:
    """
    載入模板市集的中繼資料。
    """
    _ensure_dirs()
    meta_path = _metadata_path()
    if not meta_path.exists():
        return _empty_frame()
    try:
        df = pd.read_parquet(meta_path)
        for column in SCHEMA:
            if column not in df.columns:
                df[column] = None
        return df[SCHEMA]
    except Exception:
        return _empty_frame()


def save_metadata(df: pd.DataFrame) -> None:
    """
    將模板中繼資料寫回檔案。
    """
    _ensure_dirs()
    meta_path = _metadata_path()
    normalized = df.copy()
    normalized = normalized.reindex(columns=SCHEMA, fill_value=None)
    normalized.to_parquet(meta_path, index=False)


def generate_template_id(prefix: str = "tpl") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def serialize_tags(tags: Iterable[str] | str | None) -> str:
    if tags is None:
        return ""
    if isinstance(tags, str):
        return tags
    return ",".join(sorted(set(tag.strip() for tag in tags if tag)))


def template_dir(template_id: str) -> Path:
    """
    取得模板儲存目錄，若不存在則建立。
    """
    path = _storage_dir() / template_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_uploaded_file(template_id: str, filename: str, data: bytes) -> Path:
    """
    將上傳檔案存入模板目錄，回傳檔案路徑。
    """
    dest_dir = template_dir(template_id)
    dest_path = dest_dir / filename
    with dest_path.open("wb") as f:
        f.write(data)
    return dest_path


def remove_template(template_id: str) -> None:
    """
    刪除模板檔案與 metadata 記錄。
    """
    df = load_metadata()
    mask = df["template_id"] == template_id
    if mask.any():
        df = df.loc[~mask].reset_index(drop=True)
        save_metadata(df)
    # 移除檔案
    path = template_dir(template_id)
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)


def upsert_template(record: Mapping) -> pd.DataFrame:
    """
    新增或更新模板記錄。若未指定 template_id 則自動產生。
    """
    df = load_metadata()
    template_id = record.get("template_id") or generate_template_id()

    now = datetime.utcnow()
    version = record.get("version") or 1
    status = record.get("status") or "draft"
    tags = serialize_tags(record.get("tags"))

    payload = {
        "template_id": template_id,
        "name": record.get("name") or "未命名模板",
        "category": record.get("category") or "",
        "format": record.get("format") or "mixed",
        "description": record.get("description") or "",
        "tags": tags,
        "version": int(version),
        "status": status,
        "license_type": record.get("license_type") or "standard",
        "price_type": record.get("price_type") or "free",
        "price": float(record.get("price") or 0.0),
        "storage_path": record.get("storage_path") or "",
        "thumbnail_path": record.get("thumbnail_path") or "",
        "author": record.get("author") or "",
        "reviewer": record.get("reviewer") or "",
        "created_at": record.get("created_at") or now.isoformat(),
        "updated_at": now.isoformat(),
        "last_reviewed_at": record.get("last_reviewed_at"),
        "extra": json.dumps(record.get("extra", {}), ensure_ascii=False),
    }

    mask = df["template_id"] == template_id
    if mask.any():
        df.loc[mask, :] = pd.DataFrame([payload], columns=SCHEMA).values
    else:
        df = pd.concat([df, pd.DataFrame([payload], columns=SCHEMA)], ignore_index=True)

    save_metadata(df)
    return df


def increment_version(template_id: str) -> pd.DataFrame:
    """
    對指定模板進行版本號累加。
    """
    df = load_metadata()
    mask = df["template_id"] == template_id
    if not mask.any():
        raise ValueError(f"找不到模板 {template_id}")
    df.loc[mask, "version"] = df.loc[mask, "version"].astype(int) + 1
    df.loc[mask, "updated_at"] = datetime.utcnow().isoformat()
    save_metadata(df)
    return df


def mark_status(
    template_id: str,
    status: str,
    reviewer: str | None = None,
    notes: str = "",
    checks: Dict[str, Any] | None = None,
) -> pd.DataFrame:
    """
    更新模板狀態（draft/approved/retired 等）。
    """
    df = load_metadata()
    mask = df["template_id"] == template_id
    if not mask.any():
        raise ValueError(f"找不到模板 {template_id}")
    df.loc[mask, "status"] = status
    df.loc[mask, "reviewer"] = reviewer or df.loc[mask, "reviewer"]
    timestamp = datetime.utcnow().isoformat()
    df.loc[mask, "last_reviewed_at"] = timestamp
    df.loc[mask, "updated_at"] = timestamp
    save_metadata(df)
    if reviewer:
        record_audit(template_id=template_id, status=status, reviewer=reviewer, notes=notes, checks=checks)
    return df


def export_metadata(to: Path) -> None:
    """
    匯出 metadata 為 CSV，以便人工檢查。
    """
    df = load_metadata()
    to.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(to, index=False, encoding="utf-8-sig")


def _load_audit_logs() -> pd.DataFrame:
    _ensure_dirs()
    audit_path = _audit_path()
    if not audit_path.exists():
        return pd.DataFrame(columns=AUDIT_COLUMNS)
    try:
        df = pd.read_parquet(audit_path)
        for column in AUDIT_COLUMNS:
            if column not in df.columns:
                df[column] = None
        return df[AUDIT_COLUMNS]
    except Exception:
        return pd.DataFrame(columns=AUDIT_COLUMNS)


def load_audit_logs(template_id: str | None = None, limit: int | None = None) -> pd.DataFrame:
    df = _load_audit_logs()
    if template_id:
        df = df[df["template_id"] == template_id]
    df = df.sort_values("timestamp", ascending=False)
    if limit:
        df = df.head(limit)
    return df


def record_audit(template_id: str, status: str, reviewer: str, notes: str = "", checks: Dict[str, Any] | None = None) -> pd.DataFrame:
    df = _load_audit_logs()
    entry = {
        "template_id": template_id,
        "timestamp": datetime.utcnow().isoformat(),
        "status": status,
        "reviewer": reviewer,
        "notes": notes,
        "checks": json.dumps(checks or {}, ensure_ascii=False),
    }
    df = pd.concat([pd.DataFrame([entry], columns=AUDIT_COLUMNS), df], ignore_index=True)
    df = df[AUDIT_COLUMNS]
    df.to_parquet(_audit_path(), index=False)
    return df


def validate_template(template_id: str) -> Dict[str, Any]:
    df = load_metadata()
    row = df[df["template_id"] == template_id]
    if row.empty:
        raise ValueError(f"找不到模板 {template_id}")
    record = row.iloc[0]
    issues = []
    storage_path = record.get("storage_path") or ""
    if not storage_path:
        issues.append("尚未上傳模板檔案")
    else:
        path = Path(storage_path)
        if not path.exists():
            issues.append("模板檔案不存在")
        elif path.stat().st_size == 0:
            issues.append("模板檔案大小為 0")
    description = record.get("description", "")
    if not description:
        issues.append("缺少模板說明")
    if not record.get("tags"):
        issues.append("缺少標籤")

    return {
        "template_id": template_id,
        "checked_at": datetime.utcnow().isoformat(),
        "ok": len(issues) == 0,
        "issues": issues,
        "storage_path": storage_path,
    }
