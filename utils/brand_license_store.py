from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Iterable, Mapping, List

import pandas as pd
from dotenv import load_dotenv
from langchain_core.documents import Document


load_dotenv()

DEFAULT_METADATA_PATH = "data/licenses/metadata.parquet"
DEFAULT_STORAGE_DIR = "data/licenses/packages"

SCHEMA = [
    "license_id",
    "name",
    "brand",
    "description",
    "tags",
    "status",
    "price_type",
    "price",
    "knowledge_path",
    "terms",
    "created_at",
    "updated_at",
    "applied_brands",
    "extra",
]


def _metadata_path() -> Path:
    return Path(os.getenv("BRAND_LICENSE_METADATA_PATH", DEFAULT_METADATA_PATH)).expanduser()


def _storage_dir() -> Path:
    return Path(os.getenv("BRAND_LICENSE_STORAGE_DIR", DEFAULT_STORAGE_DIR)).expanduser()


def _ensure_dirs() -> None:
    meta = _metadata_path()
    meta.parent.mkdir(parents=True, exist_ok=True)
    storage = _storage_dir()
    storage.mkdir(parents=True, exist_ok=True)


def _empty_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=SCHEMA)


def load_metadata() -> pd.DataFrame:
    _ensure_dirs()
    meta = _metadata_path()
    if not meta.exists():
        return _empty_frame()
    try:
        df = pd.read_parquet(meta)
        for column in SCHEMA:
            if column not in df.columns:
                df[column] = None
        return df[SCHEMA]
    except Exception:
        return _empty_frame()


def save_metadata(df: pd.DataFrame) -> None:
    _ensure_dirs()
    meta = _metadata_path()
    normalized = df.copy()
    normalized = normalized.reindex(columns=SCHEMA, fill_value=None)
    normalized.to_parquet(meta, index=False)


def serialize_tags(tags: Iterable[str] | str | None) -> str:
    if tags is None:
        return ""
    if isinstance(tags, str):
        return tags
    return ",".join(sorted(set(tag.strip() for tag in tags if tag)))


def upsert_license(record: Mapping) -> pd.DataFrame:
    df = load_metadata()
    license_id = record.get("license_id") or f"lic_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
    now = datetime.utcnow().isoformat()
    payload = {
        "license_id": license_id,
        "name": record.get("name") or "未命名授權方案",
        "brand": record.get("brand") or "",
        "description": record.get("description") or "",
        "tags": serialize_tags(record.get("tags")),
        "status": record.get("status") or "draft",
        "price_type": record.get("price_type") or "one_time",
        "price": float(record.get("price") or 0.0),
        "knowledge_path": record.get("knowledge_path") or "",
        "terms": record.get("terms") or "",
        "created_at": record.get("created_at") or now,
        "updated_at": now,
        "applied_brands": json.dumps(record.get("applied_brands", []), ensure_ascii=False),
        "extra": json.dumps(record.get("extra", {}), ensure_ascii=False),
    }

    mask = df["license_id"] == license_id
    if mask.any():
        df.loc[mask, :] = pd.DataFrame([payload], columns=SCHEMA).values
    else:
        df = pd.concat([df, pd.DataFrame([payload], columns=SCHEMA)], ignore_index=True)
    save_metadata(df)
    return df


def get_license(license_id: str) -> dict | None:
    df = load_metadata()
    row = df[df["license_id"] == license_id]
    if row.empty:
        return None
    record = row.iloc[0].to_dict()
    try:
        record["applied_brands"] = json.loads(record.get("applied_brands") or "[]")
    except json.JSONDecodeError:
        record["applied_brands"] = []
    try:
        record["extra"] = json.loads(record.get("extra") or "{}")
    except json.JSONDecodeError:
        record["extra"] = {}
    return record


def register_application(license_id: str, brand_code: str, applied_by: str = "") -> pd.DataFrame:
    df = load_metadata()
    mask = df["license_id"] == license_id
    if not mask.any():
        raise ValueError(f"找不到授權方案 {license_id}")

    applied = df.loc[mask, "applied_brands"].iloc[0]
    try:
        applied_list = json.loads(applied) if applied else []
    except json.JSONDecodeError:
        applied_list = []

    applied_list.append(
        {
            "brand_code": brand_code,
            "applied_by": applied_by,
            "applied_at": datetime.utcnow().isoformat(),
        }
    )
    df.loc[mask, "applied_brands"] = json.dumps(applied_list, ensure_ascii=False)
    df.loc[mask, "updated_at"] = datetime.utcnow().isoformat()
    save_metadata(df)
    return df


def delete_license(license_id: str) -> None:
    df = load_metadata()
    df = df[df["license_id"] != license_id]
    save_metadata(df)

    package_dir = _storage_dir() / license_id
    if package_dir.exists():
        shutil.rmtree(package_dir, ignore_errors=True)


def license_dir(license_id: str) -> Path:
    path = _storage_dir() / license_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_knowledge_file(license_id: str, filename: str, data: bytes) -> Path:
    dest = license_dir(license_id) / filename
    with dest.open("wb") as f:
        f.write(data)
    return dest


def _knowledge_base_path(record: dict) -> Path:
    path = record.get("knowledge_path")
    if path:
        return Path(path).expanduser()
    return license_dir(record["license_id"])


def load_knowledge_documents(record: dict, brand_code: str) -> List[Document]:
    base = _knowledge_base_path(record)
    if not base.exists():
        return []

    documents: List[Document] = []
    for file in base.glob("**/*"):
        if file.is_dir():
            continue
        if file.suffix.lower() not in {".txt", ".md", ".json"}:
            continue
        try:
            text = file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = file.read_text(encoding="utf-8", errors="ignore")

        metadata = {
            "type": "brand_knowledge",
            "license_id": record["license_id"],
            "brand": record.get("brand", ""),
            "brand_code": brand_code,
            "source_file": file.name,
            "tags": record.get("tags", ""),
            "applied_at": datetime.utcnow().isoformat(),
        }
        documents.append(Document(page_content=text, metadata=metadata))
    return documents


def apply_license_to_brand(
    license_id: str,
    brand_code: str,
    rag_service=None,
    collection_name: str = "brand_knowledge",
) -> int:
    record = get_license(license_id)
    if not record:
        raise ValueError(f"找不到授權方案 {license_id}")

    documents = load_knowledge_documents(record, brand_code=brand_code)
    if not documents:
        raise ValueError("授權方案缺少知識庫內容，請先上傳文本")

    if rag_service is not None:
        rag_service.add_documents(documents, collection_name=collection_name)
    register_application(license_id, brand_code)
    return len(documents)
