#!/usr/bin/env python3
"""
建立授權試點示例資料，方便在前台查看導入紀錄。

使用方式：
    python scripts/seed_license_pilots.py
"""

from __future__ import annotations

from utils import license_pilot_tracker


SAMPLE_EVENTS = [
    {
        "license_id": "lic_brand_voice_default",
        "brand_code": "HAHOW_TEA",
        "status": "success",
        "metrics": {"adoption_rate": 0.85, "weeks_in_use": 3},
        "notes": "完成門市與電商文案導入，反饋正面。",
        "recorded_by": "pm_amy",
    },
    {
        "license_id": "lic_brand_voice_default",
        "brand_code": "HAHOW_TEA",
        "status": "in_progress",
        "metrics": {"adoption_rate": 0.92, "weeks_in_use": 4},
        "notes": "即將完成 CRM 模板導入。",
        "recorded_by": "pm_amy",
    },
    {
        "license_id": "lic_limited_autumn",
        "brand_code": "FARMHOUSE_BAKERY",
        "status": "success",
        "metrics": {"campaign_uplift": 18},
        "notes": "秋季聯名活動採用，廣告 ROAS 提升 18%。",
        "recorded_by": "cs_brian",
    },
]


def main() -> None:
    for event in SAMPLE_EVENTS:
        license_pilot_tracker.log_pilot_event(**event)
    print(f"已建立 {len(SAMPLE_EVENTS)} 筆授權試點紀錄。")


if __name__ == "__main__":
    main()
