"""MVT 設計 Agent (Pydantic AI)."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Any, Optional

import pandas as pd
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext


class FactorLevel(BaseModel):
    factor: str = Field(description="實驗因子")
    levels: list[str] = Field(description="測試層級")
    rationale: str = Field(description="選擇理由")


class MVTPlan(BaseModel):
    hypothesis: str = Field(description="核心假設")
    factors: list[FactorLevel] = Field(description="實驗因子設定")
    primary_metric: str = Field(description="主要指標")
    interaction_focus: list[str] = Field(description="關注交互作用")
    required_runs: int = Field(description="所需組合數")
    phased_rollout: list[str] = Field(description="分階段上線")


class MVTDesignResult(BaseModel):
    plan: MVTPlan = Field(description="完整實驗計畫")
    data_collection_plan: list[str] = Field(description="資料蒐集需求")
    analysis_framework: list[str] = Field(description="分析方法")
    risk_controls: list[str] = Field(description="風險控管")
    stakeholders: list[str] = Field(description="利害關係人")


@dataclass
class MVTDesignDeps:
    df: pd.DataFrame
    variables: dict[str, list[str]]
    test_objective: str
    baseline_rate: float
    minimum_detectable_effect: float
    expected_daily_traffic: int
    design_template: Optional[dict[str, Any]] = None
    analytics_toolkit: Optional[Any] = None
    launch_calendar: Optional[list[str]] = None


class MVTDesignAgent:
    """多變量測試設計 Agent."""

    def __init__(self) -> None:
        model_name = os.getenv("OPENAI_MODEL", "gpt-5-nano")
        self.agent = Agent(
            f"openai:{model_name}",
            output_type=MVTDesignResult,
            deps_type=MVTDesignDeps,
            system_prompt=self._system_prompt(),
        )
        self._register_tools()

    def _system_prompt(self) -> str:
        return """
你是一位專業的廣告多變量測試（MVT）顧問。
提供的工具會包含目前變數設定、樣本估算、歷史表現與排程限制。
請產出完全符合 `MVTDesignResult` 結構的繁體中文輸出，內容要具體、可執行。
"""

    def _register_tools(self) -> None:
        @self.agent.tool
        def variable_blueprint(ctx: RunContext[MVTDesignDeps]) -> dict[str, Any]:
            variables = ctx.deps.variables or {}
            total_combinations = _calc_total_combinations(variables)
            complexity = _complexity_label(total_combinations)
            return {
                "variables": variables,
                "total_variables": len(variables),
                "total_combinations": total_combinations,
                "complexity": complexity,
            }

        @self.agent.tool
        def sample_estimation(ctx: RunContext[MVTDesignDeps]) -> dict[str, Any]:
            combos = _calc_total_combinations(ctx.deps.variables)
            sample_per_variant = _estimate_sample_size(
                combos,
                ctx.deps.baseline_rate,
                ctx.deps.minimum_detectable_effect,
            )
            total_sample = sample_per_variant * combos
            daily = max(ctx.deps.expected_daily_traffic, 1)
            required_days = math.ceil(total_sample / daily)
            return {
                "baseline_rate": ctx.deps.baseline_rate,
                "mde": ctx.deps.minimum_detectable_effect,
                "sample_per_variant": sample_per_variant,
                "total_sample": total_sample,
                "expected_daily_traffic": ctx.deps.expected_daily_traffic,
                "estimated_days": required_days,
            }

        @self.agent.tool
        def dataset_insights(ctx: RunContext[MVTDesignDeps]) -> dict[str, Any]:
            df = ctx.deps.df
            if df.empty:
                return {"available": False}

            grouped = df.groupby('行銷活動名稱', as_index=False).agg({
                '花費金額 (TWD)': 'sum',
                '購買 ROAS（廣告投資報酬率）': 'mean',
                'CTR（全部）': 'mean',
                '購買次數': 'sum'
            }).rename(columns={'CTR（全部）': 'ctr'})

            top_campaigns = (
                grouped.sort_values('購買 ROAS（廣告投資報酬率）', ascending=False)
                .head(5)
                .to_dict('records')
            )

            median_roas = float(grouped['購買 ROAS（廣告投資報酬率）'].median()) if not grouped.empty else None
            median_ctr = float(grouped['ctr'].median()) if not grouped.empty else None

            return {
                "available": True,
                "top_campaigns": top_campaigns,
                "median_roas": median_roas,
                "median_ctr": median_ctr,
                "span": _calc_date_span(df),
            }

        @self.agent.tool
        def launch_constraints(ctx: RunContext[MVTDesignDeps]) -> dict[str, Any]:
            return {
                "launch_calendar": ctx.deps.launch_calendar or [],
            }

        @self.agent.tool
        def design_templates(ctx: RunContext[MVTDesignDeps]) -> dict[str, Any]:
            template = ctx.deps.design_template or {}
            return {"design_template": template}

    async def design(
        self,
        df: pd.DataFrame,
        variables: dict[str, list[str]],
        test_objective: str,
        baseline_rate: float,
        minimum_detectable_effect: float,
        expected_daily_traffic: int,
        design_template: Optional[dict[str, Any]] = None,
        analytics_toolkit: Optional[Any] = None,
        launch_calendar: Optional[list[str]] = None,
    ) -> MVTDesignResult:
        deps = MVTDesignDeps(
            df=df,
            variables=variables,
            test_objective=test_objective,
            baseline_rate=baseline_rate,
            minimum_detectable_effect=minimum_detectable_effect,
            expected_daily_traffic=expected_daily_traffic,
            design_template=design_template,
            analytics_toolkit=analytics_toolkit,
            launch_calendar=launch_calendar,
        )
        combos = _calc_total_combinations(variables)
        prompt = f"""
測試目標：{test_objective}
變數設定：{variables}
總組合數：{combos}
基準轉換率：{baseline_rate:.4f}
最小可檢測效應（MDE）：{minimum_detectable_effect:.4f}
預期每日流量：{expected_daily_traffic}

請：
1. 評估是否適合進行 MVT 與預期複雜度
2. 產出完整的 MVT 測試計畫（含假設與分階段策略）
3. 指定資料蒐集與分析方法
4. 提出風險控管與護欄建議
5. 標註關鍵利害關係人與責任分工
"""
        result = await self.agent.run(prompt, deps=deps)
        return result.output

    def design_sync(
        self,
        df: pd.DataFrame,
        variables: dict[str, list[str]],
        test_objective: str,
        baseline_rate: float,
        minimum_detectable_effect: float,
        expected_daily_traffic: int,
        design_template: Optional[dict[str, Any]] = None,
        analytics_toolkit: Optional[Any] = None,
        launch_calendar: Optional[list[str]] = None,
    ) -> MVTDesignResult:
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.design(
                df=df,
                variables=variables,
                test_objective=test_objective,
                baseline_rate=baseline_rate,
                minimum_detectable_effect=minimum_detectable_effect,
                expected_daily_traffic=expected_daily_traffic,
                design_template=design_template,
                analytics_toolkit=analytics_toolkit,
                launch_calendar=launch_calendar,
            )
        )


def _calc_total_combinations(variables: dict[str, list[str]]) -> int:
    total = 1
    for options in variables.values():
        total *= max(len(options), 1)
    return total


def _complexity_label(total: int) -> str:
    if total <= 10:
        return "🟢 簡單"
    if total <= 20:
        return "🟡 中等"
    return "🔴 複雜"


def _estimate_sample_size(
    total_combinations: int,
    baseline_rate: float,
    mde: float,
    alpha: float = 0.05,
    power: float = 0.8,
) -> int:
    from scipy.stats import norm

    baseline_rate = max(baseline_rate, 1e-4)
    mde = max(mde, 1e-4)

    p1 = baseline_rate
    p2 = baseline_rate * (1 + mde)

    z_alpha = norm.ppf(1 - alpha / (2 * max(total_combinations, 1)))
    z_beta = norm.ppf(power)
    p_avg = (p1 + p2) / 2

    numerator = (
        z_alpha * math.sqrt(2 * p_avg * (1 - p_avg))
        + z_beta * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
    )
    denominator = abs(p1 - p2)
    if denominator == 0:
        return 0
    n = (numerator ** 2) / (denominator ** 2)
    return max(int(math.ceil(n)), 0)


def _calc_date_span(df: pd.DataFrame) -> Optional[str]:
    date_cols = [col for col in df.columns if '開始' in col or '日期' in col]
    if not date_cols:
        return None
    try:
        dates = pd.to_datetime(df[date_cols[0]], errors='coerce').dropna()
        if dates.empty:
            return None
        start = dates.min().strftime('%Y-%m-%d')
        end = dates.max().strftime('%Y-%m-%d')
        return f"{start} ~ {end}"
    except Exception:
        return None


__all__ = [
    "MVTDesignAgent",
    "MVTDesignResult",
]
