"""成本分析工具。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import pandas as pd


@dataclass
class CostSummary:
    current_monthly_cost: float
    optimization_opportunities: List[Dict[str, float]]
    total_potential_savings: float
    savings_percentage: float


class CostAnalyzer:
    def analyze_cost_breakdown(self, logs: pd.DataFrame) -> pd.DataFrame:
        if logs.empty:
            return pd.DataFrame(columns=["model", "cost"])
        return (
            logs.groupby("model")['cost']
            .sum()
            .reset_index()
            .sort_values('cost', ascending=False)
        )

    def identify_optimization_opportunities(self, logs: pd.DataFrame) -> List[Dict[str, float]]:
        opportunities: List[Dict[str, float]] = []
        if logs.empty:
            return opportunities

        expensive = logs[logs['model'].str.contains('gpt-4', case=False, na=False)]
        if not expensive.empty:
            opportunities.append({
                'type': '高價模型使用過多',
                'impact': 'high',
                'potential_savings': float(expensive['cost'].sum() * 0.5),
            })
        return opportunities

    def generate_report(self, logs: pd.DataFrame) -> CostSummary:
        breakdown = self.analyze_cost_breakdown(logs)
        opportunities = self.identify_optimization_opportunities(logs)
        total_cost = float(logs['cost'].sum()) if not logs.empty else 0.0
        total_savings = sum(item['potential_savings'] for item in opportunities)
        percentage = (total_savings / total_cost * 100) if total_cost else 0.0
        return CostSummary(
            current_monthly_cost=total_cost,
            optimization_opportunities=opportunities,
            total_potential_savings=total_savings,
            savings_percentage=percentage,
        )


__all__ = ["CostAnalyzer", "CostSummary"]
