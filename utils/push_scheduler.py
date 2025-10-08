from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

import pandas as pd


DEFAULT_CHANNEL = "Slack"
DEFAULT_WINDOW_START = 9


def _default_send_time(now: datetime) -> datetime:
    planned = now.replace(hour=DEFAULT_WINDOW_START, minute=0, second=0, microsecond=0)
    if now >= planned:
        planned = planned + timedelta(days=1)
    return planned


def generate_push_plan(
    scores: pd.DataFrame,
    channel: str = DEFAULT_CHANNEL,
    per_campaign: int = 2,
    send_at: Optional[datetime] = None,
) -> pd.DataFrame:
    if scores.empty:
        return pd.DataFrame(columns=[
            "campaign_id",
            "creative_id",
            "risk_tier",
            "fatigue_score",
            "cta",
            "message",
            "channel",
            "send_at",
        ])

    now = datetime.utcnow()
    planned_time = send_at or _default_send_time(now)

    high_risk = scores[scores["risk_tier"].isin(["高風險", "中風險"])]
    ranked = (
        high_risk.sort_values(["risk_tier", "fatigue_score"], ascending=[True, False])
        .groupby("campaign_id")
        .head(per_campaign)
        .reset_index(drop=True)
    )

    def _build_cta(row: pd.Series) -> str:
        base = "建議立即替換素材"
        if row.get("ctr") and row["ctr"] < 1:
            base = "檢查投放受眾/版位"
        if row.get("roas") and row["roas"] < 1:
            base += "；檢討銷售漏斗"
        return base

    def _build_message(row: pd.Series) -> str:
        reasons = row.get("reasons", [])
        if isinstance(reasons, list):
            reason_text = "；".join(reasons[:2])
        else:
            reason_text = str(reasons)
        return (
            f"【疲勞預警】活動 {row['campaign_id']} 的素材 {row['creative_id']} 評估為{row['risk_tier']}，"
            f"疲勞分數 {row['fatigue_score']:.2f}。原因：{reason_text}。"
        )

    ranked["cta"] = ranked.apply(_build_cta, axis=1)
    ranked["message"] = ranked.apply(_build_message, axis=1)
    ranked["channel"] = channel
    ranked["send_at"] = planned_time.isoformat()

    return ranked[[
        "campaign_id",
        "creative_id",
        "risk_tier",
        "fatigue_score",
        "cta",
        "message",
        "channel",
        "send_at",
    ]]


def compile_digest(plan: pd.DataFrame) -> List[str]:
    if plan.empty:
        return []
    digest: List[str] = []
    for _, row in plan.iterrows():
        digest.append(
            f"活動 {row['campaign_id']} → 素材 {row['creative_id']} ({row['risk_tier']})：{row['cta']}"
        )
    return digest
