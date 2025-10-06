"""
廣告品質評分 Agent (Pydantic AI)

功能：
- 評估 Meta 廣告的品質/互動/轉換排名
- 尋找低品質廣告與根本原因
- 提供優先處理的優化建議與實驗方案
- 可整合 RAG 歷史案例

特色：
- 完全型別安全輸出
- 工具負責資料整理，LLM 產出洞察
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import pandas as pd
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext


class QualityIssue(BaseModel):
    priority: str = Field(description="優先級（🔴/🟡/🟢）")
    title: str = Field(description="問題描述")
    description: str = Field(description="詳細說明")
    impacted_ads: list[str] = Field(default_factory=list, description="受影響廣告")
    recommended_actions: list[str] = Field(default_factory=list, description="建議措施")
    metrics_to_watch: list[str] = Field(default_factory=list, description="後續追蹤指標")


class QualitySummary(BaseModel):
    overall_status: str = Field(description="整體品質評估")
    health_score: int = Field(ge=0, le=100, description="品質健康度")
    strengths: list[str] = Field(default_factory=list, description="亮點")
    weaknesses: list[str] = Field(default_factory=list, description="弱點")
    improvement_focus: list[str] = Field(default_factory=list, description="需聚焦的改善方向")


class QualityExperiment(BaseModel):
    name: str = Field(description="實驗名稱")
    hypothesis: str = Field(description="假設")
    steps: list[str] = Field(default_factory=list, description="執行步驟")
    expected_outcome: str = Field(description="預期結果")


class QualityAnalysisResult(BaseModel):
    summary: QualitySummary
    issues: list[QualityIssue]
    experiments: list[QualityExperiment]


@dataclass
class QualityScoreDeps:
    df: pd.DataFrame
    rag_service: Optional[object] = None


class QualityScoreAgent:
    """廣告品質評分 Agent"""

    def __init__(self) -> None:
        model_name = os.getenv('OPENAI_MODEL', 'gpt-5-nano')
        self.agent = Agent(
            f'openai:{model_name}',
            output_type=QualityAnalysisResult,
            deps_type=QualityScoreDeps,
            system_prompt=self._get_system_prompt(),
        )
        self._register_tools()

    def _get_system_prompt(self) -> str:
        return """
你是 Meta 廣告品質評估顧問，擅長分析品質排名、互動率排名與轉換率排名，並提供可執行的優化策略。請產出符合 `QualityAnalysisResult` 的結構，使用繁體中文。
"""

    def _register_tools(self) -> None:
        @self.agent.tool
        def compute_quality_distribution(ctx: RunContext[QualityScoreDeps]) -> dict:
            df = ctx.deps.df
            columns = ['品質排名', '互動率排名', '轉換率排名']
            distribution = {}
            for col in columns:
                if col in df.columns:
                    distribution[col] = df[col].value_counts().to_dict()
            return {'distribution': distribution}

        @self.agent.tool
        def compute_score_stats(ctx: RunContext[QualityScoreDeps]) -> dict:
            df = ctx.deps.df
            score_cols = [col for col in df.columns if col.endswith('分數')]
            stats = {}
            for col in score_cols:
                stats[col] = {
                    'mean': float(df[col].mean()),
                    'median': float(df[col].median()),
                    'max': float(df[col].max()),
                    'min': float(df[col].min()),
                }
            return {'score_stats': stats}

        @self.agent.tool
        def detect_low_quality_ads(ctx: RunContext[QualityScoreDeps]) -> dict:
            df = ctx.deps.df
            if '品質排名' not in df:
                return {'low_quality_ads': []}
            low_ads = df[df['品質排名'] == '平均以下']
            ads = []
            for _, row in low_ads.iterrows():
                ads.append({
                    'ad_name': row.get('廣告名稱', '未知'),
                    'campaign': row.get('行銷活動名稱', '未知'),
                    'spend': float(row.get('花費金額 (TWD)', 0)),
                    'roas': float(row.get('購買 ROAS（廣告投資報酬率）', 0)),
                    'ctr': float(row.get('CTR（全部）', 0) * 100),
                    'engagement_rank': row.get('互動率排名'),
                    'conversion_rank': row.get('轉換率排名'),
                })
            return {'low_quality_ads': ads[:20]}

        @self.agent.tool
        def load_rag_examples(ctx: RunContext[QualityScoreDeps]) -> dict:
            rag = ctx.deps.rag_service
            if not rag:
                return {'available': False}
            try:
                docs = rag.search_similar_ads('廣告 品質 提升 案例', top_k=3)
                results = []
                for doc in docs:
                    results.append({
                        'content': getattr(doc, 'page_content', ''),
                        'metadata': getattr(doc, 'metadata', {})
                    })
                return {'available': True, 'examples': results}
            except Exception:
                return {'available': False}

    async def analyze(self, df: pd.DataFrame, rag_service: Optional[object] = None) -> QualityAnalysisResult:
        deps = QualityScoreDeps(df=df, rag_service=rag_service)
        prompt = """
請綜合工具輸出的品質資料，整理成：
1. 整體品質摘要（含健康分數、亮點、弱點）
2. 至少三個優先處理的問題與對應建議
3. 2-3 個品質提升實驗方案
"""
        result = await self.agent.run(prompt, deps=deps)
        return result.output

    def analyze_sync(self, df: pd.DataFrame, rag_service: Optional[object] = None) -> QualityAnalysisResult:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.analyze(df, rag_service))
