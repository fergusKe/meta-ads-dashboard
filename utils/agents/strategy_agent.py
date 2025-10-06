"""智能投放策略 Agent (Pydantic AI)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional

import pandas as pd
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext


class StrategicPillar(BaseModel):
    name: str = Field(description="策略主軸")
    objective: str = Field(description="目標")
    key_results: list[str] = Field(description="關鍵成果指標")
    tactical_moves: list[str] = Field(description="戰術建議")


class StrategyAgentResult(BaseModel):
    horizon: str = Field(description="規劃期間")
    strategic_pillars: list[StrategicPillar] = Field(description="策略主軸清單")
    budget_allocation: dict[str, float] = Field(description="預算分配建議")
    audience_strategy: list[str] = Field(description="受眾策略")
    creative_strategy: list[str] = Field(description="創意策略")
    measurement_plan: list[str] = Field(description="衡量計畫")
    executive_summary: str = Field(description="主管摘要")


@dataclass
class StrategyAgentDeps:
    df: pd.DataFrame
    top_ads: list[dict[str, Any]]
    audience_insights: dict[str, Any]
    business_goals: dict[str, Any]
    planning_horizon: str
    total_budget: float
    market_forecast: Optional[dict[str, Any]] = None
    inventory_constraints: Optional[dict[str, Any]] = None
    notes: Optional[list[str]] = None


class StrategyAgent:
    """智能投放策略 Agent."""

    def __init__(self) -> None:
        model_name = os.getenv("OPENAI_MODEL", "gpt-5-nano")
        self.agent = Agent(
            f"openai:{model_name}",
            output_type=StrategyAgentResult,
            deps_type=StrategyAgentDeps,
            system_prompt=self._system_prompt(),
        )
        self._register_tools()

    def _system_prompt(self) -> str:
        return """
你是 Meta 廣告策略總監，熟悉全漏斗策略、受眾拓展與預算規劃。
使用提供的工具了解目前表現，再產生符合 `StrategyAgentResult` 結構的策略方案。
輸出需為繁體中文，且具體、可執行。
"""

    def _register_tools(self) -> None:
        @self.agent.tool
        def account_snapshot(ctx: RunContext[StrategyAgentDeps]) -> dict[str, Any]:
            df = ctx.deps.df
            if df.empty:
                return {"available": False}
            total_spend = float(df['花費金額 (TWD)'].sum()) if '花費金額 (TWD)' in df else 0.0
            total_purchase = float(df['購買次數'].sum()) if '購買次數' in df else 0.0
            avg_roas = float(df['購買 ROAS（廣告投資報酬率）'].mean()) if '購買 ROAS（廣告投資報酬率）' in df else None
            avg_ctr = float(df['CTR（全部）'].mean()) if 'CTR（全部）' in df else None
            return {
                "available": True,
                "total_spend": total_spend,
                "total_purchase": total_purchase,
                "avg_roas": avg_roas,
                "avg_ctr": avg_ctr,
                "date_span": _calc_date_span(df),
            }

        @self.agent.tool
        def campaign_highlights(ctx: RunContext[StrategyAgentDeps]) -> dict[str, Any]:
            top_ads = ctx.deps.top_ads or []
            return {
                "top_ads": top_ads[:5],
            }

        @self.agent.tool
        def audience_breakdown(ctx: RunContext[StrategyAgentDeps]) -> dict[str, Any]:
            insights = ctx.deps.audience_insights or {}
            return {
                "audience": insights,
            }

        @self.agent.tool
        def goal_context(ctx: RunContext[StrategyAgentDeps]) -> dict[str, Any]:
            return {
                "business_goals": ctx.deps.business_goals,
                "planning_horizon": ctx.deps.planning_horizon,
                "total_budget": ctx.deps.total_budget,
                "inventory_constraints": ctx.deps.inventory_constraints or {},
            }

        @self.agent.tool
        def market_signals(ctx: RunContext[StrategyAgentDeps]) -> dict[str, Any]:
            return {
                "market_forecast": ctx.deps.market_forecast or {},
                "notes": ctx.deps.notes or [],
            }

    async def craft_strategy(
        self,
        df: pd.DataFrame,
        top_ads: list[dict[str, Any]],
        audience_insights: dict[str, Any],
        business_goals: dict[str, Any],
        planning_horizon: str,
        total_budget: float,
        market_forecast: Optional[dict[str, Any]] = None,
        inventory_constraints: Optional[dict[str, Any]] = None,
        notes: Optional[list[str]] = None,
    ) -> StrategyAgentResult:
        deps = StrategyAgentDeps(
            df=df,
            top_ads=top_ads,
            audience_insights=audience_insights,
            business_goals=business_goals,
            planning_horizon=planning_horizon,
            total_budget=total_budget,
            market_forecast=market_forecast,
            inventory_constraints=inventory_constraints,
            notes=notes,
        )
        prompt = """
請根據目前帳戶表現、受眾洞察與商業目標，產出季度級的投放策略：
1. 定義 2-3 個策略主軸與對應的關鍵成果指標
2. 規劃預算在不同策略主軸或渠道的分配（可用百分比或金額）
3. 提出具體的受眾與創意策略
4. 設計衡量與回顧節奏，並提醒可能的風險
5. 形成主管摘要（50 字內）
"""
        result = await self.agent.run(prompt, deps=deps)
        return result.output

    def craft_strategy_sync(
        self,
        df: pd.DataFrame,
        top_ads: list[dict[str, Any]],
        audience_insights: dict[str, Any],
        business_goals: dict[str, Any],
        planning_horizon: str,
        total_budget: float,
        market_forecast: Optional[dict[str, Any]] = None,
        inventory_constraints: Optional[dict[str, Any]] = None,
        notes: Optional[list[str]] = None,
    ) -> StrategyAgentResult:
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.craft_strategy(
                df=df,
                top_ads=top_ads,
                audience_insights=audience_insights,
                business_goals=business_goals,
                planning_horizon=planning_horizon,
                total_budget=total_budget,
                market_forecast=market_forecast,
                inventory_constraints=inventory_constraints,
                notes=notes,
            )
        )


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
    "StrategyAgent",
    "StrategyAgentResult",
]
