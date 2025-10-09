"""
自動化報告 Agent (Pydantic AI)

功能：
- 統整指定期間的核心指標
- 比較期與前期表現差異
- 彙整高效 / 低效活動與關鍵事件
- 產出可執行的行動計畫與策略建議

特色：
- 完全型別安全輸出
- 工具負責指標計算，LLM 負責報告撰寫
"""

from __future__ import annotations

import os
from datetime import datetime
from pydantic.dataclasses import dataclass
from typing import Optional

import pandas as pd
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext


class MetricComparison(BaseModel):
    name: str = Field(description="指標名稱")
    current_value: float = Field(description="本期數值")
    previous_value: Optional[float] = Field(default=None, description="前期數值")
    change_percent: Optional[float] = Field(default=None, description="變化百分比")


class CampaignHighlight(BaseModel):
    name: str = Field(description="活動或廣告名稱")
    spend: float = Field(description="花費 (TWD)")
    roas: float = Field(description="ROAS")
    ctr: Optional[float] = Field(default=None, description="CTR (%)")
    conversions: Optional[float] = Field(default=None, description="轉換次數")
    notes: Optional[str] = Field(default=None, description="補充說明或成功因素")


class ActionPlanItem(BaseModel):
    priority: str = Field(description="優先級（🔴/🟡/🟢）")
    action: str = Field(description="具體動作")
    expected_impact: str = Field(description="預期成效")
    timeline: str = Field(description="建議時程")


class StrategyRecommendation(BaseModel):
    title: str = Field(description="策略建議標題")
    description: str = Field(description="詳細說明")


class ReportSummary(BaseModel):
    report_type: str = Field(description="報告類型（週報 / 月報 / 自訂）")
    period: str = Field(description="報告期間描述")
    overall_status: str = Field(description="整體狀態說明")
    key_insights: list[str] = Field(description="核心洞察", default_factory=list)
    metrics: list[MetricComparison]


class ReportGenerationResult(BaseModel):
    summary: ReportSummary
    successes: list[CampaignHighlight]
    issues: list[CampaignHighlight]
    action_plan: list[ActionPlanItem]
    strategies: list[StrategyRecommendation]


@dataclass(config=dict(arbitrary_types_allowed=True))
class ReportGenerationDeps:
    df: pd.DataFrame
    current_start: datetime
    current_end: datetime
    previous_start: Optional[datetime]
    previous_end: Optional[datetime]
    rag_service: Optional[object] = None


class ReportGenerationAgent:
    """自動化報告 Agent"""

    def __init__(self) -> None:
        model_name = os.getenv('OPENAI_MODEL', 'gpt-5-nano')
        self.agent = Agent(
            f'openai:{model_name}',
            output_type=ReportGenerationResult,
            deps_type=ReportGenerationDeps,
            system_prompt=self._get_system_prompt(),
        )
        self._register_tools()

    def _get_system_prompt(self) -> str:
        return """
你是一名專業的 Meta 廣告投放分析師，要撰寫主管級的自動化報告。
輸出需符合 `ReportGenerationResult` 結構並使用繁體中文，內容需具體、可執行。
"""

    def _register_tools(self) -> None:
        @self.agent.tool
        def compute_metrics(ctx: RunContext[ReportGenerationDeps]) -> dict:
            df = ctx.deps.df
            start, end = ctx.deps.current_start, ctx.deps.current_end
            current = df[(df['開始'] >= start) & (df['開始'] <= end)]
            metrics = _aggregate_metrics(current)
            result = {'current_metrics': metrics}
            if ctx.deps.previous_start is not None and ctx.deps.previous_end is not None:
                prev = df[(df['開始'] >= ctx.deps.previous_start) & (df['開始'] <= ctx.deps.previous_end)]
                result['previous_metrics'] = _aggregate_metrics(prev)
            return result

        @self.agent.tool
        def campaign_performance(ctx: RunContext[ReportGenerationDeps]) -> dict:
            df = ctx.deps.df
            start, end = ctx.deps.current_start, ctx.deps.current_end
            period = df[(df['開始'] >= start) & (df['開始'] <= end)]
            if period.empty:
                return {'top_campaigns': [], 'low_campaigns': []}
            grouped = period.groupby('行銷活動名稱', as_index=False).agg({
                '花費金額 (TWD)': 'sum',
                '購買 ROAS（廣告投資報酬率）': 'mean',
                '購買次數': 'sum',
                'CTR（全部）': 'mean'
            })
            top = grouped.sort_values('購買 ROAS（廣告投資報酬率）', ascending=False).head(5)
            low = grouped[grouped['花費金額 (TWD)'] >= grouped['花費金額 (TWD)'].median()]\
                .sort_values('購買 ROAS（廣告投資報酬率）', ascending=True).head(5)
            return {
                'top_campaigns': top.to_dict('records'),
                'low_campaigns': low.to_dict('records'),
            }

        @self.agent.tool
        def detect_events(ctx: RunContext[ReportGenerationDeps]) -> dict:
            df = ctx.deps.df
            start, end = ctx.deps.current_start, ctx.deps.current_end
            period = df[(df['開始'] >= start) & (df['開始'] <= end)]
            events = []
            if period.empty:
                return {'events': events}
            # 新活動
            if '開始' in period.columns:
                new_campaigns = period.groupby('行銷活動名稱')['開始'].min()
                new_campaigns = new_campaigns[new_campaigns >= start]
                if not new_campaigns.empty:
                    events.append({
                        'type': '新活動上線',
                        'count': int(len(new_campaigns)),
                        'examples': list(new_campaigns.index[:3])
                    })
            # 預算異常
            if '花費金額 (TWD)' in period.columns:
                daily = period.groupby('開始')['花費金額 (TWD)'].sum()
                if not daily.empty:
                    avg = daily.mean()
                    max_spend = daily.max()
                    if max_spend > avg * 1.5:
                        events.append({
                            'type': '預算異常',
                            'detail': f'單日花費 {max_spend:,.0f} (平均 {avg:,.0f})'
                        })
            return {'events': events}

        @self.agent.tool
        def load_rag_examples(ctx: RunContext[ReportGenerationDeps]) -> dict:
            rag = ctx.deps.rag_service
            if not rag:
                return {'available': False}
            try:
                docs = rag.search_similar_ads('報告 重點 行動 建議', top_k=3)
                examples = []
                for doc in docs:
                    examples.append({
                        'content': getattr(doc, 'page_content', ''),
                        'metadata': getattr(doc, 'metadata', {})
                    })
                return {'available': True, 'examples': examples}
            except Exception:
                return {'available': False}

    async def generate(
        self,
        df: pd.DataFrame,
        current_start: pd.Timestamp,
        current_end: pd.Timestamp,
        previous_start: Optional[pd.Timestamp] = None,
        previous_end: Optional[pd.Timestamp] = None,
        rag_service: Optional[object] = None,
    ) -> ReportGenerationResult:
        deps = ReportGenerationDeps(
            df=df,
            current_start=current_start,
            current_end=current_end,
            previous_start=previous_start,
            previous_end=previous_end,
            rag_service=rag_service,
        )
        prompt = """
請整合提供的指標與活動資料，撰寫完整報告：
- 整體摘要與健康評估
- 核心指標比較 (花費、ROAS、購買、CTR 等)
- Top 3 成功案例
- 至少 3 個需改善項目與建議
- 優先排序的行動計畫
- 2-3 個策略建議
報告需具體、可執行。
"""
        result = await self.agent.run(prompt, deps=deps)
        return result.output

    def generate_sync(
        self,
        df: pd.DataFrame,
        current_start: pd.Timestamp,
        current_end: pd.Timestamp,
        previous_start: Optional[pd.Timestamp] = None,
        previous_end: Optional[pd.Timestamp] = None,
        rag_service: Optional[object] = None,
    ) -> ReportGenerationResult:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(
            self.generate(
                df=df,
                current_start=current_start,
                current_end=current_end,
                previous_start=previous_start,
                previous_end=previous_end,
                rag_service=rag_service,
            )
        )


def _aggregate_metrics(df: pd.DataFrame) -> dict[str, float]:
    if df.empty:
        return {
            'spend': 0.0,
            'revenue': 0.0,
            'purchases': 0.0,
            'ctr': 0.0,
            'roas': 0.0,
            'cpa': 0.0,
        }
    spend = float(df['花費金額 (TWD)'].sum()) if '花費金額 (TWD)' in df else 0.0
    roas_series = df['購買 ROAS（廣告投資報酬率）'] if '購買 ROAS（廣告投資報酬率）' in df else pd.Series([0])
    roas = float(roas_series.mean()) if not roas_series.empty else 0.0
    revenue = float(spend * roas)
    purchases = float(df['購買次數'].sum()) if '購買次數' in df else 0.0
    ctr_series = df['CTR（全部）'] if 'CTR（全部）' in df else pd.Series([0])
    ctr = float(ctr_series.mean() * 100)
    cpa_series = df['每次購買的成本'] if '每次購買的成本' in df else pd.Series([0])
    cpa = float(cpa_series.mean())
    return {
        'spend': spend,
        'revenue': revenue,
        'purchases': purchases,
        'ctr': ctr,
        'roas': roas,
        'cpa': cpa,
    }
