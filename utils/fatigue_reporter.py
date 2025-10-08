from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import pandas as pd

from . import fatigue_analyzer


def _default_report() -> Dict[str, Any]:
    return {
        "generated_at": datetime.utcnow().isoformat(),
        "total_creatives": 0,
        "high_risk": 0,
        "medium_risk": 0,
        "low_risk": 0,
        "top_creatives": [],
        "campaign_summary": [],
        "recommendations": [],
    }


def generate_report(scores: pd.DataFrame, top_n: int = 10) -> Dict[str, Any]:
    report = _default_report()
    if scores.empty:
        report["recommendations"].append("尚無素材資料，請先同步素材成效。")
        return report

    report["total_creatives"] = int(len(scores))
    report["high_risk"] = int((scores["risk_tier"] == "高風險").sum())
    report["medium_risk"] = int((scores["risk_tier"] == "中風險").sum())
    report["low_risk"] = int((scores["risk_tier"] == "低風險").sum())

    top_creatives = scores.sort_values("fatigue_score", ascending=False).head(top_n)
    # ensure reasons serializable (list)
    sanitized = top_creatives.copy()
    sanitized["reasons"] = sanitized["reasons"].apply(lambda items: list(items) if isinstance(items, (list, tuple)) else [items])
    report["top_creatives"] = sanitized.to_dict(orient="records")

    campaign_summary = fatigue_analyzer.summarize_by_campaign(scores)
    report["campaign_summary"] = campaign_summary.to_dict(orient="records") if not campaign_summary.empty else []

    recommendations: list[str] = []
    if report["high_risk"]:
        recommendations.append(
            f"共有 {report['high_risk']} 則素材落在高風險區間，請優先更新或替換這些素材。"
        )
    if report["medium_risk"]:
        recommendations.append(
            f"{report['medium_risk']} 則素材為中風險，建議排程 A/B 測試並監控 7 日內指標。"
        )
    if report["low_risk"] and report["high_risk"] == 0:
        recommendations.append("目前沒有高風險素材，可維持現行投放節奏並持續監測。")
    if not campaign_summary.empty and "avg_score" in campaign_summary.columns:
        worst_campaign = campaign_summary.sort_values("avg_score", ascending=False).head(1)
        if not worst_campaign.empty:
            campaign_id = worst_campaign.iloc[0]["campaign_id"]
            recommendations.append(f"活動 {campaign_id} 平均疲勞分數最高，建議安排創意刷新計畫。")
    if not recommendations:
        recommendations.append("建議持續收集更多素材表現資料，以提升預測準確度。")
    report["recommendations"] = recommendations
    return report


def export_report(report: Dict[str, Any], destination: str | Path) -> Path:
    path = Path(destination).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return path
