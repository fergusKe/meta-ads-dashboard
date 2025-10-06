"""
受眾擴展建議 Agent (Pydantic AI)

功能：
- 分析現有受眾的表現指標
- 識別可擴展的高效受眾群與新受眾提案
- 提供 Lookalike 策略與觀察指標
- 支援整合歷史案例 (RAG)

特色：
- 使用 Pydantic 定義完整輸出結構
- 工具負責計算數據摘要，LLM 專注策略化建議
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import pandas as pd
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext


class CoreAudience(BaseModel):
    """現有高效受眾摘要"""

    age: str = Field(description="年齡描述")
    gender: str = Field(description="性別")
    interest: str = Field(description="目標/興趣")
    roas: float = Field(description="平均 ROAS")
    ctr: float = Field(description="平均 CTR (%)")
    spend: float = Field(description="花費 (TWD)")
    conversions: float = Field(description="轉換次數")


class ExpansionAudience(BaseModel):
    """新受眾建議"""

    title: str = Field(description="受眾名稱/描述")
    similarity: str = Field(description="與既有成功受眾的相似度")
    demo_profile: str = Field(description="人口 + 興趣輪廓")
    expected_roas: str = Field(description="預期 ROAS 或表現評估")
    test_budget: str = Field(description="建議測試預算")
    test_duration: str = Field(description="建議測試期")
    success_metrics: list[str] = Field(description="成功指標", default_factory=list)
    priority: str = Field(description="優先級 (🔴/🟡/🟢)")


class LookalikeStrategy(BaseModel):
    """Lookalike 擴展方案"""

    source_audience: str = Field(description="基礎來源受眾")
    similarity: str = Field(description="相似度範圍 (1%-10%)")
    regions: list[str] = Field(description="建議投放地區", default_factory=list)
    rationale: str = Field(description="策略理由")
    expected_scale: str = Field(description="預期受眾規模/成效")


class WatchoutAudience(BaseModel):
    """應避免或低優先的受眾"""

    description: str = Field(description="受眾描述")
    reason: str = Field(description="建議避免的理由")


class ExecutionPlan(BaseModel):
    """30 天執行計畫"""

    week: str = Field(description="週別")
    focus: list[str] = Field(description="該週行動重點", default_factory=list)


class AudienceSummary(BaseModel):
    """整體摘要"""

    health_status: str = Field(description="受眾投放健康度評估")
    key_insights: list[str] = Field(description="關鍵洞察", default_factory=list)
    recommended_metrics: list[str] = Field(description="建議追蹤指標", default_factory=list)


class AudienceExpansionResult(BaseModel):
    """受眾擴展分析輸出"""

    summary: AudienceSummary
    core_audiences: list[CoreAudience]
    expansion_audiences: list[ExpansionAudience]
    lookalike_strategies: list[LookalikeStrategy]
    watchout_audiences: list[WatchoutAudience]
    execution_plan: list[ExecutionPlan]


@dataclass
class AudienceExpansionDeps:
    df: pd.DataFrame
    rag_service: Optional[object] = None


class AudienceExpansionAgent:
    """受眾擴展 Agent"""

    def __init__(self) -> None:
        model_name = os.getenv('OPENAI_MODEL', 'gpt-5-nano')
        self.agent = Agent(
            f'openai:{model_name}',
            output_type=AudienceExpansionResult,
            deps_type=AudienceExpansionDeps,
            system_prompt=self._get_system_prompt(),
        )
        self._register_tools()

    def _get_system_prompt(self) -> str:
        return """
你是專業的 Meta 廣告受眾策略顧問。請根據現有受眾表現提供可執行的擴展建議。輸出需符合 `AudienceExpansionResult`，並以繁體中文呈現。
"""

    def _register_tools(self) -> None:
        @self.agent.tool
        def summarize_core_audiences(ctx: RunContext[AudienceExpansionDeps]) -> dict:
            df = ctx.deps.df
            if '年齡' not in df or '性別' not in df or '目標' not in df:
                return {'core_audiences': []}
            grouped = df.groupby(['年齡', '性別', '目標'], as_index=False).agg({
                '購買 ROAS（廣告投資報酬率）': 'mean',
                'CTR（全部）': 'mean',
                '花費金額 (TWD)': 'sum',
                '購買次數': 'sum'
            }).sort_values('購買 ROAS（廣告投資報酬率）', ascending=False)
            results = []
            for _, row in grouped.iterrows():
                results.append({
                    'age': str(row['年齡']),
                    'gender': str(row['性別']),
                    'interest': str(row['目標']),
                    'roas': float(row['購買 ROAS（廣告投資報酬率）']),
                    'ctr': float(row['CTR（全部）'] * 100),
                    'spend': float(row['花費金額 (TWD)']),
                    'conversions': float(row['購買次數'])
                })
            return {'core_audiences': results[:10]}

        @self.agent.tool
        def fetch_audience_distribution(ctx: RunContext[AudienceExpansionDeps]) -> dict:
            df = ctx.deps.df
            distribution = {}
            if '目標' in df:
                distribution['goal'] = df['目標'].value_counts().to_dict()
            if '地區' in df:
                distribution['region'] = df['地區'].value_counts().to_dict()
            if '裝置' in df:
                distribution['device'] = df['裝置'].value_counts().to_dict()
            return {'distribution': distribution}

        @self.agent.tool
        def load_rag_examples(ctx: RunContext[AudienceExpansionDeps]) -> dict:
            rag = ctx.deps.rag_service
            if not rag:
                return {'available': False}
            try:
                docs = rag.search_similar_ads('受眾 擴展 策略', top_k=3)
                examples = []
                for doc in docs:
                    examples.append({
                        'content': getattr(doc, 'page_content', ''),
                        'metadata': getattr(doc, 'metadata', {})
                    })
                return {'available': True, 'examples': examples}
            except Exception:
                return {'available': False}

    async def analyze(
        self,
        df: pd.DataFrame,
        rag_service: Optional[object] = None,
    ) -> AudienceExpansionResult:
        deps = AudienceExpansionDeps(df=df, rag_service=rag_service)
        prompt = """
請整合工具輸出資料，提供：
1. 現有高效受眾摘要
2. 5-8 個受眾擴展提案（含描述、相似度、測試策略、優先級）
3. Lookalike 建議
4. 避免或低優先受眾清單
5. 30 天執行計畫 (Week 1-4)
"""
        result = await self.agent.run(prompt, deps=deps)
        return result.output

    def analyze_sync(
        self,
        df: pd.DataFrame,
        rag_service: Optional[object] = None,
    ) -> AudienceExpansionResult:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.analyze(df, rag_service))
