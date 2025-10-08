from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Mapping, Sequence, Tuple, Dict, Any

import pandas as pd
from dotenv import load_dotenv

from . import template_store


load_dotenv()

SUPPORTED_EXTENSIONS = {".csv", ".json", ".xlsx", ".parquet"}
REQUIRED_FIELDS = {"name", "category"}
DEFAULT_RECORD = {
    "format": "mixed",
    "description": "",
    "tags": [],
    "license_type": "standard",
    "price_type": "free",
    "price": 0.0,
    "author": "",
    "status": "draft",
}


def _ingest_log_path() -> Path:
    path = os.getenv("TEMPLATE_INGEST_LOG_PATH", "data/templates/ingest_logs.parquet")
    return Path(path).expanduser()


def _ensure_log_dir() -> None:
    log_path = _ingest_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)


def _load_log() -> pd.DataFrame:
    _ensure_log_dir()
    path = _ingest_log_path()
    if not path.exists():
        return pd.DataFrame(columns=[
            "batch_id",
            "template_id",
            "name",
            "action",
            "timestamp",
            "source",
            "notes",
        ])
    try:
        return pd.read_parquet(path)
    except Exception:
        return pd.DataFrame(columns=["batch_id", "template_id", "name", "action", "timestamp", "source", "notes"])


def _save_log(df: pd.DataFrame) -> None:
    _ensure_log_dir()
    df.to_parquet(_ingest_log_path(), index=False)


def _parse_tags(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        if not value.strip():
            return []
        return [tag.strip() for tag in value.split(",") if tag.strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(tag).strip() for tag in value if str(tag).strip()]
    return []


def _parse_extra(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return {}
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
    return {"raw": value}


def _read_json(path: Path) -> pd.DataFrame:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        if "records" in data and isinstance(data["records"], list):
            return pd.DataFrame(data["records"])
        return pd.DataFrame([data])
    if isinstance(data, list):
        return pd.DataFrame(data)
    raise ValueError(f"JSON 檔案 {path} 無法轉換為表格。")


def load_dataframe_from_file(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"不支援的檔案格式：{path.suffix}")
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix == ".json":
        return _read_json(path)
    if suffix == ".xlsx":
        return pd.read_excel(path)
    if suffix == ".parquet":
        return pd.read_parquet(path)
    raise ValueError(f"不支援的檔案格式：{path.suffix}")


def load_sources(paths: Iterable[str | Path]) -> pd.DataFrame:
    frames: List[pd.DataFrame] = []
    for item in paths:
        path = Path(item)
        if path.is_dir():
            files = sorted(file for file in path.iterdir() if file.suffix.lower() in SUPPORTED_EXTENSIONS)
            if not files:
                continue
            frames.append(load_sources(files))
            continue
        frames.append(load_dataframe_from_file(path))
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def _copy_file(template_id: str, source: str | Path | None) -> str:
    if not source:
        return ""
    path = Path(source)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"找不到檔案：{source}")
    data = path.read_bytes()
    saved = template_store.save_uploaded_file(template_id, path.name, data)
    return saved.as_posix()


@dataclass
class IngestSummary:
    created: int
    updated: int
    errors: List[str]
    batch_id: str


def _normalize_record(raw: Mapping[str, Any], defaults: Mapping[str, Any] | None = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    defaults = {**DEFAULT_RECORD, **(defaults or {})}
    record = {key: raw.get(key, defaults.get(key)) for key in set(DEFAULT_RECORD) | set(raw.keys())}
    missing = [field for field in REQUIRED_FIELDS if not str(record.get(field, "")).strip()]
    if missing:
        raise ValueError(f"缺少必要欄位：{', '.join(missing)} (資料：{raw})")

    record["template_id"] = record.get("template_id") or template_store.generate_template_id()
    record["tags"] = _parse_tags(record.get("tags"))
    record["extra"] = _parse_extra(record.get("extra"))
    record["price"] = float(record.get("price") or 0.0)
    record["author"] = record.get("author") or defaults.get("author", "")
    record["status"] = record.get("status") or "draft"

    attachments = {
        "file_path": raw.get("file_path") or defaults.get("file_path"),
        "thumbnail_path": raw.get("thumbnail_path") or defaults.get("thumbnail_path"),
    }
    return record, attachments


def ingest_dataframe(df: pd.DataFrame, defaults: Mapping[str, Any] | None = None, source: str = "") -> IngestSummary:
    if df.empty:
        return IngestSummary(created=0, updated=0, errors=[], batch_id="")

    batch_id = f"ingest_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
    metadata = template_store.load_metadata()
    existing_ids = set(metadata["template_id"]) if not metadata.empty else set()

    created = 0
    updated = 0
    errors: List[str] = []
    log_df = _load_log()

    for raw_record in df.to_dict(orient="records"):
        try:
            normalized, attachments = _normalize_record(raw_record, defaults)
            template_id = normalized["template_id"]
            was_existing = template_id in existing_ids

            if attachments["file_path"]:
                normalized["storage_path"] = _copy_file(template_id, attachments["file_path"])
            if attachments["thumbnail_path"]:
                normalized["thumbnail_path"] = _copy_file(template_id, attachments["thumbnail_path"])

            template_store.upsert_template(normalized)
            action = "updated" if was_existing else "created"
            if was_existing:
                updated += 1
            else:
                created += 1
                existing_ids.add(template_id)

            log_entry = {
                "batch_id": batch_id,
                "template_id": template_id,
                "name": normalized.get("name", ""),
                "action": action,
                "timestamp": datetime.utcnow().isoformat(),
                "source": source or raw_record.get("source") or "",
                "notes": raw_record.get("notes", ""),
            }
            log_df = pd.concat([log_df, pd.DataFrame([log_entry])], ignore_index=True)
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))

    if not log_df.empty:
        _save_log(log_df)

    return IngestSummary(created=created, updated=updated, errors=errors, batch_id=batch_id)


def ingest_from_files(
    paths: Sequence[str | Path],
    defaults: Mapping[str, Any] | None = None,
) -> IngestSummary:
    if not paths:
        return IngestSummary(created=0, updated=0, errors=["未提供匯入來源"], batch_id="")

    frames: List[pd.DataFrame] = []
    for path in paths:
        resolved = Path(path)
        if resolved.is_dir():
            for child in sorted(resolved.iterdir()):
                if child.suffix.lower() in SUPPORTED_EXTENSIONS:
                    frames.append(load_dataframe_from_file(child))
        else:
            frames.append(load_dataframe_from_file(resolved))

    if not frames:
        return IngestSummary(created=0, updated=0, errors=["找不到可匯入的檔案"], batch_id="")

    combined = pd.concat(frames, ignore_index=True)
    return ingest_dataframe(combined, defaults=defaults, source=", ".join(str(Path(p)) for p in paths))

