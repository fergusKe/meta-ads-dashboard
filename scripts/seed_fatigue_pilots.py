#!/usr/bin/env python3
"""
建立素材疲勞試點示例資料，便於在疲勞預測頁面查看成果。

使用方式：
    python scripts/seed_fatigue_pilots.py
"""

from __future__ import annotations

from utils import fatigue_pilot_manager


SAMPLE_RESULTS = [
    {
        "creative_id": "CRV_A001",
        "campaign_id": "CMP_FALL_FLASH",
        "action_taken": "refresh_creative",
        "outcome": "success",
        "metrics": {"lift": 22.4, "ctr_after": 2.1},
        "notes": "更換關鍵視覺後 CTR 提升顯著。",
        "recorded_by": "analyst_jay",
    },
    {
        "creative_id": "CRV_A001",
        "campaign_id": "CMP_FALL_FLASH",
        "action_taken": "monitor",
        "outcome": "monitor",
        "metrics": {"lift": 6.3},
        "notes": "第二週持續觀察，保持穩定。",
        "recorded_by": "analyst_jay",
    },
    {
        "creative_id": "CRV_B014",
        "campaign_id": "CMP_HOLIDAY_GIFT",
        "action_taken": "adjust_budget",
        "outcome": "fail",
        "metrics": {"lift": -4.2},
        "notes": "雖調整預算但素材仍老化，建議替換。",
        "recorded_by": "analyst_cindy",
    },
]


def main() -> None:
    for result in SAMPLE_RESULTS:
        fatigue_pilot_manager.log_pilot_result(**result)
    print(f"已建立 {len(SAMPLE_RESULTS)} 筆素材疲勞試點紀錄。")


if __name__ == "__main__":
    main()
