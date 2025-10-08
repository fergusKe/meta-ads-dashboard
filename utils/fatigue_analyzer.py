from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Optional

import pandas as pd

from . import creative_store


DEFAULT_CONFIG: Dict[str, float] = {
    "age_threshold_days": 14.0,
    "roas_target": 2.5,
    "ctr_target": 1.5,
    "spend_threshold": 5000.0,
    "weight_age": 0.35,
    "weight_roas": 0.35,
    "weight_ctr": 0.2,
    "weight_spend": 0.1,
}


@dataclass
class FatigueResult:
    creative_id: str
    campaign_id: str
    status: str
    asset_type: str
    age_days: float
    spend: float
    roas: float
    ctr: float
    impressions: float
    conversions: float
    fatigue_score: float
    risk_tier: str
    reasons: List[str]


def _ensure_datetime(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    converted = df.copy()
    for column in columns:
        if column in converted.columns:
            converted[column] = pd.to_datetime(converted[column], errors="coerce")
    return converted


def _compute_reason_list(row: pd.Series, config: Dict[str, float]) -> List[str]:
    reasons: List[str] = []
    if row.get("age_days", 0) >= config["age_threshold_days"]:
        reasons.append(f"投放 {row['age_days']:.0f} 天，超出 {int(config['age_threshold_days'])} 天門檻")
    roas = row.get("roas")
    if pd.notna(roas) and roas < config["roas_target"]:
        reasons.append(f"ROAS {roas:.2f} 低於目標 {config['roas_target']}")
    ctr = row.get("ctr")
    if pd.notna(ctr) and ctr < config["ctr_target"]:
        reasons.append(f"CTR {ctr:.2f}% 低於目標 {config['ctr_target']}%")
    spend = row.get("spend", 0)
    if spend >= config["spend_threshold"]:
        reasons.append(f"累積花費 NT$ {spend:,.0f}，高於 {config['spend_threshold']:,.0f}")
    if not reasons:
        reasons.append("指標接近門檻，建議持續觀察")
    return reasons


def _assign_risk(score: float) -> str:
    if score >= 0.7:
        return "高風險"
    if score >= 0.45:
        return "中風險"
    return "低風險"


def calculate_fatigue_scores(
    df: pd.DataFrame,
    config: Optional[Dict[str, float]] = None,
    reference_datetime: Optional[datetime] = None,
) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=[
            "creative_id",
            "campaign_id",
            "status",
            "asset_type",
            "age_days",
            "spend",
            "roas",
            "ctr",
            "impressions",
            "conversions",
            "fatigue_score",
            "risk_tier",
            "reasons",
        ])

    cfg = {**DEFAULT_CONFIG, **(config or {})}
    reference = pd.Timestamp(reference_datetime or datetime.utcnow())

    prepared = _ensure_datetime(df, ["generated_at", "approved_at", "deployed_at", "retired_at", "last_updated_at"])
    prepared = prepared.copy()
    for column in ["deployed_at", "approved_at", "generated_at"]:
        if column not in prepared.columns:
            prepared[column] = pd.NaT
    prepared["deployed_at"] = prepared["deployed_at"].fillna(prepared["approved_at"]).fillna(prepared["generated_at"])  # type: ignore[arg-type]
    for column in ["spend", "roas", "ctr", "impressions", "conversions"]:
        if column not in prepared.columns:
            prepared[column] = None
    prepared["age_days"] = (reference - prepared["deployed_at"]).dt.days.clip(lower=0)

    def _norm(value: Optional[float], target: float, reverse: bool = False) -> float:
        if value is None or pd.isna(value):
            return 0.5
        value = float(value)
        if reverse:
            normalized = min(value / target, 1.0) if target else 0.0
        else:
            if target == 0:
                return 0.0
            normalized = max(0.0, min(1.0, 1 - (value / target)))
        return normalized

    prepared["age_component"] = (prepared["age_days"] / cfg["age_threshold_days"]).clip(0, 1)
    prepared["roas_component"] = prepared["roas"].apply(lambda v: _norm(v, cfg["roas_target"]))
    prepared["ctr_component"] = prepared["ctr"].apply(lambda v: _norm(v, cfg["ctr_target"]))
    prepared["spend_component"] = prepared["spend"].apply(lambda v: _norm(v, cfg["spend_threshold"], reverse=True))

    prepared["fatigue_score"] = (
        prepared["age_component"] * cfg["weight_age"]
        + prepared["roas_component"] * cfg["weight_roas"]
        + prepared["ctr_component"] * cfg["weight_ctr"]
        + prepared["spend_component"] * cfg["weight_spend"]
    )

    prepared["risk_tier"] = prepared["fatigue_score"].apply(_assign_risk)
    prepared["reasons"] = prepared.apply(lambda row: _compute_reason_list(row, cfg), axis=1)

    result = prepared[[
        "creative_id",
        "campaign_id",
        "status",
        "asset_type",
        "age_days",
        "spend",
        "roas",
        "ctr",
        "impressions",
        "conversions",
        "fatigue_score",
        "risk_tier",
        "reasons",
    ]].copy()
    result.sort_values("fatigue_score", ascending=False, inplace=True)
    return result.reset_index(drop=True)


def summarize_by_campaign(scores: pd.DataFrame) -> pd.DataFrame:
    if scores.empty:
        return scores
    summary = (
        scores.groupby("campaign_id")
        .agg(
            creatives=("creative_id", "nunique"),
            high_risk=("risk_tier", lambda s: (s == "高風險").sum()),
            medium_risk=("risk_tier", lambda s: (s == "中風險").sum()),
            avg_score=("fatigue_score", "mean"),
            avg_roas=("roas", "mean"),
        )
        .reset_index()
        .sort_values("avg_score", ascending=False)
    )
    return summary


def load_and_score(config: Optional[Dict[str, float]] = None) -> pd.DataFrame:
    df = creative_store.load_performance_data()
    return calculate_fatigue_scores(df, config=config)
