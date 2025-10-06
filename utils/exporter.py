"""匯出與分享工具。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import pandas as pd

EXPORT_DIR = Path("data/exports")
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


def export_json(data: Dict[str, Any], prefix: str = "export") -> Path:
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = EXPORT_DIR / f"{prefix}_{timestamp}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def export_dataframe(df: pd.DataFrame, prefix: str = "export") -> Path:
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = EXPORT_DIR / f"{prefix}_{timestamp}.csv"
    df.to_csv(path, index=False)
    return path


__all__ = ["export_json", "export_dataframe"]
