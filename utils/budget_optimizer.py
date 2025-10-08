from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import pandas as pd


@dataclass
class BudgetConfig:
    target_roas: float = 2.0
    min_donor_spend: float = 5000.0
    shift_ratio: float = 0.2
    max_recipients: int = 5


def _aggregate_campaigns(df: pd.DataFrame) -> pd.DataFrame:
    required = {"行銷活動名稱", "花費金額 (TWD)", "購買 ROAS（廣告投資報酬率）"}
    if not required.issubset(df.columns):
        raise ValueError("缺少必要欄位：行銷活動名稱 / 花費金額 (TWD) / 購買 ROAS（廣告投資報酬率）")

    group = (
        df.groupby("行銷活動名稱", as_index=False)
        .agg(
            spend=("花費金額 (TWD)", "sum"),
            roas=("購買 ROAS（廣告投資報酬率）", "mean"),
            conversions=("購買次數", "sum") if "購買次數" in df.columns else ("花費金額 (TWD)", "size"),
        )
    )
    if "conversions" in group.columns and group["conversions"].dtype == "float64":
        group["conversions"].fillna(0, inplace=True)
    return group


def generate_reallocation_plan(df: pd.DataFrame, config: Optional[BudgetConfig] = None) -> pd.DataFrame:
    cfg = config or BudgetConfig()
    aggregated = _aggregate_campaigns(df)
    if aggregated.empty:
        return pd.DataFrame(columns=[
            "campaign",
            "current_spend",
            "suggested_spend",
            "delta",
            "roas",
            "conversions",
            "role",
            "notes",
        ])

    donors = aggregated[(aggregated["roas"] < cfg.target_roas) & (aggregated["spend"] >= cfg.min_donor_spend)].copy()
    donors["delta"] = -(donors["spend"] * cfg.shift_ratio)

    recipients = aggregated[aggregated["roas"] >= cfg.target_roas].copy()
    recipients = recipients.sort_values("roas", ascending=False).head(cfg.max_recipients)

    total_freed = donors["delta"].sum() * -1
    if total_freed <= 0 or recipients.empty:
        return pd.DataFrame(columns=[
            "campaign",
            "current_spend",
            "suggested_spend",
            "delta",
            "roas",
            "conversions",
            "role",
            "notes",
        ])

    weight = recipients["roas"] * (recipients.get("conversions", 1) + 1)
    total_weight = weight.sum()
    recipients["delta"] = 0.0
    if total_weight > 0:
        recipients["delta"] = total_freed * (weight / total_weight)

    donor_rows = donors.assign(role="donor")
    donor_rows["suggested_spend"] = donor_rows["spend"] + donor_rows["delta"]
    donor_rows["notes"] = donor_rows["delta"].apply(lambda x: f"釋出 {abs(x):,.0f} 以調整低 ROAS")

    recipient_rows = recipients.assign(role="recipient")
    recipient_rows["suggested_spend"] = recipient_rows["spend"] + recipient_rows["delta"]
    recipient_rows["notes"] = recipient_rows["delta"].apply(lambda x: f"追加 {x:,.0f} 強化高 ROAS")

    combined = pd.concat([donor_rows, recipient_rows], ignore_index=True)
    combined.rename(columns={
        "行銷活動名稱": "campaign",
        "spend": "current_spend",
        "roas": "roas",
    }, inplace=True)
    ordered = combined[[
        "campaign",
        "role",
        "current_spend",
        "suggested_spend",
        "delta",
        "roas",
        "conversions",
        "notes",
    ]].copy()
    ordered.sort_values(["role", "delta"], ascending=[True, True], inplace=True)
    return ordered.reset_index(drop=True)


def summarize_shift(plan: pd.DataFrame) -> Dict[str, float]:
    if plan.empty:
        return {"freed": 0.0, "reallocated": 0.0}
    freed = plan[plan["role"] == "donor"]["delta"].sum() * -1
    gain = plan[plan["role"] == "recipient"]["delta"].sum()
    return {"freed": round(float(freed), 2), "reallocated": round(float(gain), 2)}
