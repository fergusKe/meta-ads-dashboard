"""
競爭對手分析 Agent (Pydantic AI)

功能：
- 整合我們的廣告表現與競品廣告素材
- 摘要競品強項、與我們的差異化優勢
- 產出差異化文案構想、應避免策略與行動建議
- 可選擇整合 RAG 歷史案例作為靈感來源
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, Sequence

import pandas as pd
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext


class CompetitorAd(BaseModel):
    brand: str
    headline: str
    body: str
    start_time: Optional[str] = None
    impressions: Optional[str] = None
    spend: Optional[str] = None


class DifferentiationIdea(BaseModel):
    title: str
    description: str
    reason: str


class ActionRecommendation(BaseModel):
    priority: str = Field(description="優先級（🔴/🟡/🟢）")
    action: str = Field(description="建議執行的動作")
    expected_impact: str = Field(description="預期成效")


class CompetitorAnalysisResult(BaseModel):
    overview: str
    competitor_strengths: list[str]
    our_differentiators: list[str]
    differentiation_ideas: list[DifferentiationIdea]
    avoid_strategies: list[str]
    market_insights: list[str]
    action_plan: list[ActionRecommendation]
    competitor_samples: list[CompetitorAd]


@dataclass
class CompetitorAnalysisDeps:
    our_ads: pd.DataFrame
    competitor_ads: Sequence[dict]
    rag_service: Optional[object] = None


class CompetitorAnalysisAgent:
    """競爭對手分析 Agent"""

    def __init__(self) -> None:
        model_name = os.getenv('OPENAI_MODEL', 'gpt-5-nano')
        self.agent = Agent(
            f'openai:{model_name}',
            output_type=CompetitorAnalysisResult,
            deps_type=CompetitorAnalysisDeps,
            system_prompt=self._get_system_prompt(),
        )
        self._register_tools()

    def _get_system_prompt(self) -> str:
        return """
你是 Meta 廣告競品分析顧問，請根據我們的廣告表現與競品素材產出完整分析。
輸出需符合 `CompetitorAnalysisResult` 結構，並使用繁體中文。
"""

    def _register_tools(self) -> None:
        @self.agent.tool
        def summarize_our_ads(ctx: RunContext[CompetitorAnalysisDeps]) -> dict:
            df = ctx.deps.our_ads
            metrics = {}
            if '購買 ROAS（廣告投資報酬率）' in df:
                metrics['avg_roas'] = float(df['購買 ROAS（廣告投資報酬率）'].mean())
            if 'CTR（全部）' in df:
                metrics['avg_ctr'] = float(df['CTR（全部）'].mean() * 100)
            if 'headline' in df:
                metrics['top_headlines'] = df['headline'].value_counts().head(5).to_dict()
            if '目標' in df:
                metrics['top_targets'] = df['目標'].value_counts().head(5).to_dict()
            return {'our_metrics': metrics}

        @self.agent.tool
        def summarize_competitors(ctx: RunContext[CompetitorAnalysisDeps]) -> dict:
            competitors = []
            for ad in ctx.deps.competitor_ads[:10]:
                competitors.append({
                    'brand': ad.get('page_name', '未知'),
                    'headline': ad.get('ad_creative_link_title', '') or '',
                    'body': (ad.get('ad_creative_body', '') or '')[:250],
                    'start_time': ad.get('ad_delivery_start_time'),
                    'impressions': _format_range(ad.get('impressions')),
                    'spend': _format_range(ad.get('spend')),
                })
            return {'competitor_ads': competitors}

        @self.agent.tool
        def load_rag_examples(ctx: RunContext[CompetitorAnalysisDeps]) -> dict:
            rag = ctx.deps.rag_service
            if not rag:
                return {'available': False}
            try:
                docs = rag.search_similar_ads('競品 分析 差異化', top_k=3)
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
        our_ads: pd.DataFrame,
        competitor_ads: Sequence[dict],
        rag_service: Optional[object] = None,
    ) -> CompetitorAnalysisResult:
        deps = CompetitorAnalysisDeps(
            our_ads=our_ads,
            competitor_ads=competitor_ads,
            rag_service=rag_service,
        )
        prompt = """
請綜合工具提供的資料，產出：
1. 總體市場與競品摘要
2. 競品強項與我們可強化的差異化亮點
3. 5 個差異化文案/策略構想（含原因）
4. 應避免的同質化策略
5. 市場洞察與趨勢判讀
6. 優先排序的行動建議
7. 範例競品素材摘要
"""
        result = await self.agent.run(prompt, deps=deps)
        return result.output

    def analyze_sync(
        self,
        our_ads: pd.DataFrame,
        competitor_ads: Sequence[dict],
        rag_service: Optional[object] = None,
    ) -> CompetitorAnalysisResult:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.analyze(our_ads, competitor_ads, rag_service))


def _format_range(value) -> Optional[str]:
    if isinstance(value, dict):
        lower = value.get('lower_bound')
        upper = value.get('upper_bound')
        if lower is not None and upper is not None:
            return f"{lower} ~ {upper}"
    return None
