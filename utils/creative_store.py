from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Iterable, Mapping

import pandas as pd
from dotenv import load_dotenv


load_dotenv()  # 確保可以讀取 .env 設定

DEFAULT_DATA_FILE = "data/ai_creative_performance.parquet"

SCHEMA = [
    "creative_id",
    "campaign_id",
    "asset_type",
    "generated_at",
    "approved_at",
    "deployed_at",
    "retired_at",
    "status",
    "prompt_version",
    "rag_snapshot_id",
    "primary_kpi",
    "roas",
    "cpa",
    "ctr",
    "spend",
    "conversions",
    "impressions",
    "lifecycle_days",
    "feedback_notes",
    "last_updated_at",
]


def _data_path() -> Path:
    path = os.getenv("AI_PERFORMANCE_DATA_PATH", DEFAULT_DATA_FILE)
    return Path(path).expanduser()


def _empty_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=SCHEMA)


def load_performance_data() -> pd.DataFrame:
    """
    載入素材成效資料表，若檔案不存在則回傳空的資料框架。
    """
    path = _data_path()
    if not path.exists():
        return _empty_frame()
    try:
        df = pd.read_parquet(path)
        # 確保欄位齊全
        for column in SCHEMA:
            if column not in df.columns:
                df[column] = None
        return df[SCHEMA]
    except Exception:
        return _empty_frame()


def save_performance_data(df: pd.DataFrame) -> None:
    """
    將素材成效資料寫回檔案，會自動建立資料夾。
    """
    path = _data_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = df.copy()
    normalized = normalized.reindex(columns=SCHEMA, fill_value=None)
    normalized.to_parquet(path, index=False)


def append_records(records: Iterable[Mapping]) -> pd.DataFrame:
    """
    追加多筆素材記錄並回傳最新資料框架。
    """
    df = load_performance_data()
    if not records:
        return df

    new_df = pd.DataFrame(list(records))
    for time_field in ["generated_at", "approved_at", "deployed_at", "retired_at", "last_updated_at"]:
        if time_field in new_df.columns:
            new_df[time_field] = pd.to_datetime(new_df[time_field], errors="coerce")

    if "last_updated_at" not in new_df.columns:
        new_df["last_updated_at"] = datetime.utcnow()
    else:
        new_df["last_updated_at"] = new_df["last_updated_at"].fillna(datetime.utcnow())

    combined = pd.concat([df, new_df], ignore_index=True)
    save_performance_data(combined)
    return combined


def upsert_record(record: Mapping, key: str = "creative_id") -> pd.DataFrame:
    """
    以指定鍵進行單筆 upsert。
    """
    df = load_performance_data()
    creative_id = record.get(key)
    if not creative_id:
        raise ValueError("record 缺少必要欄位 creative_id")

    mask = df[key] == creative_id
    updated = pd.DataFrame([record])
    for time_field in ["generated_at", "approved_at", "deployed_at", "retired_at", "last_updated_at"]:
        if time_field in updated.columns:
            updated[time_field] = pd.to_datetime(updated[time_field], errors="coerce")
    if "last_updated_at" not in updated.columns:
        updated["last_updated_at"] = datetime.utcnow()

    if mask.any():
        df.loc[mask, :] = updated.reindex(columns=df.columns).values
    else:
        df = pd.concat([df, updated.reindex(columns=df.columns, fill_value=None)], ignore_index=True)

    save_performance_data(df)
    return df


def build_records_from_meta_ads(df: pd.DataFrame) -> list[dict]:
    """
    將 Meta 廣告原始資料轉換為素材成效資料結構。
    """
    if df.empty:
        return []

    records: list[dict] = []
    now = datetime.utcnow()

    for _, row in df.iterrows():
        creative_id = (
            row.get("廣告編號")
            or row.get("廣告編號.1")
            or row.get("廣告名稱")
        )
        if not creative_id:
            continue

        start_time = row.get("開始")
        end_time = row.get("結束時間")
        if pd.notna(start_time):
            start_time = pd.to_datetime(start_time, errors="coerce")
        else:
            start_time = None
        if pd.notna(end_time):
            end_time = pd.to_datetime(end_time, errors="coerce")
        else:
            end_time = None

        roas = row.get("購買 ROAS（廣告投資報酬率）")
        ctr = row.get("CTR（全部）")
        spend = row.get("花費金額 (TWD)")
        conversions = row.get("購買次數")
        impressions = row.get("曝光次數")

        status = "deployed"
        delivery = row.get("投遞狀態")
        if isinstance(delivery, str):
            if "停止" in delivery or "結束" in delivery:
                status = "retired"
            elif "審核" in delivery:
                status = "approved"

        lifecycle_days = None
        if start_time is not None and end_time is not None:
            delta = (end_time - start_time).days
            lifecycle_days = max(delta, 0)

        record = {
            "creative_id": str(creative_id),
            "campaign_id": row.get("行銷活動名稱"),
            "asset_type": "video" if pd.notna(row.get("影片播放次數")) else "headline",
            "generated_at": start_time,
            "approved_at": start_time,
            "deployed_at": start_time,
            "retired_at": end_time,
            "status": status,
            "prompt_version": "baseline",
            "rag_snapshot_id": None,
            "primary_kpi": row.get("成果類型") or row.get("成果"),
            "roas": float(roas) if pd.notna(roas) else None,
            "cpa": float(row.get("每次購買的成本")) if pd.notna(row.get("每次購買的成本")) else None,
            "ctr": float(ctr) * 100 if pd.notna(ctr) else None,
            "spend": float(spend) if pd.notna(spend) else None,
            "conversions": float(conversions) if pd.notna(conversions) else None,
            "impressions": float(impressions) if pd.notna(impressions) else None,
            "lifecycle_days": lifecycle_days,
            "feedback_notes": "",
            "last_updated_at": now,
        }
        records.append(record)

    return records


def sync_from_meta_ads(df: pd.DataFrame) -> pd.DataFrame:
    """
    依據 Meta 廣告原始資料建立 / 更新素材成效資料。
    """
    records = build_records_from_meta_ads(df)
    if not records:
        return load_performance_data()
    target = pd.DataFrame(records)
    save_performance_data(target)
    return target
