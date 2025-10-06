"""
A/B 測試設計 Agent (Pydantic AI)

功能：
- 分析現有數據推導 A/B 測試假設
- 產出測試變因、成功指標、樣本與時程建議
- 提供執行檢查清單與進階策略
- 可整合 RAG 案例提供靈感

特色：
- 完全型別安全輸出
- 工具整理基礎指標，LLM 負責策略化內容
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import pandas as pd
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext


class MetricSnapshot(BaseModel):
    name: str
    value: float


class TestVariation(BaseModel):
    name: str = Field(description="變體名稱或描述")
    details: str = Field(description="變體內容")


class TestIdea(BaseModel):
    priority: str = Field(description="優先級（🔴/🟡/🟢）")
    variable: str = Field(description="測試變因")
    hypothesis: str = Field(description="假設")
    success_metrics: list[str] = Field(description="成功指標", default_factory=list)
    guardrail_metrics: list[str] = Field(description="護欄指標", default_factory=list)
    test_duration: str = Field(description="建議測試期")
    budget_allocation: str = Field(description="預算或流量配置")
    expected_impact: str = Field(description="預期成效")
    variations: list[TestVariation] = Field(description="變體設計", default_factory=list)


class ABExecutionChecklist(BaseModel):
    before: list[str]
    during: list[str]
    after: list[str]


class AdvancedRecommendation(BaseModel):
    title: str
    description: str


class ABTestDesignResult(BaseModel):
    overall_summary: str
    baseline_metrics: list[MetricSnapshot]
    test_ideas: list[TestIdea]
    sample_size_notes: list[str]
    risk_management: list[str]
    execution_checklist: ABExecutionChecklist
    advanced_strategies: list[AdvancedRecommendation]


@dataclass
class ABTestDesignDeps:
    df: pd.DataFrame
    objective: str
    rag_service: Optional[object] = None


class ABTestDesignAgent:
    """A/B 測試設計 Agent"""

    def __init__(self) -> None:
        model_name = os.getenv('OPENAI_MODEL', 'gpt-5-nano')
        self.agent = Agent(
            f'openai:{model_name}',
            output_type=ABTestDesignResult,
            deps_type=ABTestDesignDeps,
            system_prompt=self._get_system_prompt(),
        )
        self._register_tools()

    def _get_system_prompt(self) -> str:
        return """
你是 Meta 廣告 A/B 測試策略專家。請依據輸入資料與工具提供完整測試設計建議，內容需符合 `ABTestDesignResult` 結構並使用繁體中文。
"""

    def _register_tools(self) -> None:
        @self.agent.tool
        def compute_baseline_metrics(ctx: RunContext[ABTestDesignDeps]) -> dict:
            df = ctx.deps.df
            metrics = []
            mapping = {
                '花費金額 (TWD)': '花費 (TWD)',
                '購買 ROAS（廣告投資報酬率）': '平均 ROAS',
                '購買次數': '總購買數',
                'CTR（全部）': '平均 CTR (%)',
                '連結點擊次數': '連結點擊數'
            }
            for col, name in mapping.items():
                if col in df:
                    value = df[col].mean() if '平均' in name else df[col].sum()
                    if col == 'CTR（全部）':
                        value *= 100
                    metrics.append({'name': name, 'value': float(value)})
            return {'baseline_metrics': metrics}

        @self.agent.tool
        def detect_opportunities(ctx: RunContext[ABTestDesignDeps]) -> dict:
            df = ctx.deps.df
            opportunities = []
            if 'headline' in df and '購買 ROAS（廣告投資報酬率）' in df:
                grouped = df.groupby('headline', as_index=False).agg({
                    '購買 ROAS（廣告投資報酬率）': 'mean',
                    '連結點擊次數': 'sum'
                })
                top = grouped[grouped['連結點擊次數'] >= 50]
                if not top.empty:
                    best = top.sort_values('購買 ROAS（廣告投資報酬率）', ascending=False).head(3)
                    worst = top.sort_values('購買 ROAS（廣告投資報酬率）', ascending=True).head(3)
                    opportunities.append({
                        'type': 'headline',
                        'best': best.to_dict('records'),
                        'worst': worst.to_dict('records'),
                    })
            if 'call_to_action_type' in df and 'CTR（全部）' in df:
                grouped = df.groupby('call_to_action_type', as_index=False)['CTR（全部）'].mean()
                opportunities.append({
                    'type': 'cta',
                    'cta_performance': grouped.to_dict('records')
                })
            return {'opportunities': opportunities}

        @self.agent.tool
        def load_rag_examples(ctx: RunContext[ABTestDesignDeps]) -> dict:
            rag = ctx.deps.rag_service
            if not rag:
                return {'available': False}
            try:
                docs = rag.search_similar_ads('A/B 測試 成功 案例', top_k=3)
                results = []
                for doc in docs:
                    results.append({
                        'content': getattr(doc, 'page_content', ''),
                        'metadata': getattr(doc, 'metadata', {})
                    })
                return {'available': True, 'examples': results}
            except Exception:
                return {'available': False}

    async def design(
        self,
        df: pd.DataFrame,
        objective: str,
        rag_service: Optional[object] = None,
    ) -> ABTestDesignResult:
        deps = ABTestDesignDeps(df=df, objective=objective, rag_service=rag_service)
        prompt = f"""
請根據工具提供的資料與測試目標「{objective}」設計完整 A/B 測試計畫。
需要包含：摘要、測試想法、樣本與風險管理、執行檢查清單、進階建議。
"""
        result = await self.agent.run(prompt, deps=deps)
        return result.output

    def design_sync(
        self,
        df: pd.DataFrame,
        objective: str,
        rag_service: Optional[object] = None,
    ) -> ABTestDesignResult:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.design(df=df, objective=objective, rag_service=rag_service))
