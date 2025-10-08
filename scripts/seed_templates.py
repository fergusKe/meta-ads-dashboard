#!/usr/bin/env python3
"""
工具：匯入預設模板樣本或指定 CSV/XLSX/JSON 檔案，便於快速建立首批模板。

使用方式：
    python scripts/seed_templates.py                       # 匯入預設 sample_templates.csv
    python scripts/seed_templates.py path/to/file.csv      # 匯入自訂檔案
    python scripts/seed_templates.py file1.csv file2.xlsx  # 可指定多個來源
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from utils import content_ingestor


DEFAULT_SAMPLE = Path("data/templates/sample_templates.csv")


def ingest(paths: Sequence[Path]) -> None:
    summary = content_ingestor.ingest_from_files([str(path) for path in paths])
    if not summary.batch_id:
        print("沒有可匯入的資料。")
        if summary.errors:
            print("錯誤：")
            for item in summary.errors:
                print(f"- {item}")
        return

    print(f"匯入批次：{summary.batch_id}")
    print(f"新增模板：{summary.created}")
    print(f"更新模板：{summary.updated}")
    if summary.errors:
        print("錯誤：")
        for item in summary.errors:
            print(f"- {item}")


def main() -> None:
    parser = argparse.ArgumentParser(description="批次匯入模板資料")
    parser.add_argument("paths", nargs="*", type=Path, help="資料檔案或資料夾路徑")
    args = parser.parse_args()

    if args.paths:
        ingest(args.paths)
        return

    if DEFAULT_SAMPLE.exists():
        print(f"未指定檔案，使用預設樣本：{DEFAULT_SAMPLE}")
        ingest([DEFAULT_SAMPLE])
    else:
        print("未指定匯入檔案，且找不到預設樣本。")


if __name__ == "__main__":
    main()
