"""
素材成效分析 Agent (Pydantic AI)

功能：
- 評估廣告素材在各指標（ROAS、CTR、轉換）上的表現
- 找出高表現與需改善的素材特徵
- 提供優化建議與實驗策略
- 支援分群比較（例如裝置、受眾、活動）

特色：
- 完全型別安全的輸出結構
- 工具整合數據統計，LLM 專注解讀與建議
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import pandas as pd
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext


class CreativeMetric(BaseModel):
    """單項素材指標摘要"""

    name: str = Field(description="素材識別（例如 Headline、CTA）")
    value: str = Field(description="素材內容")
    roas: float = Field(description="平均 ROAS")
    ctr: float = Field(description="平均 CTR (%)")
    cpa: Optional[float] = Field(default=None, description="平均 CPA")
    conversions: float = Field(description="總轉換次數")
    impressions: float = Field(description="曝光次數")
    spend: float = Field(description="花費金額 (TWD)")


class CreativeInsight(BaseModel):
    """素材洞察"""

    title: str = Field(description="洞察標題")
    description: str = Field(description="詳細說明")
    supporting_examples: list[str] = Field(description="佐證例子", default_factory=list)


class OptimizationIdea(BaseModel):
    """優化建議"""

    priority: str = Field(description="優先級（🔴/🟡/🟢）")
    focus_area: str = Field(description="優化焦點，例如文案、圖片或 CTA")
    action_steps: list[str] = Field(description="建議步驟", default_factory=list)
    expected_impact: str = Field(description="預期效果")
    metrics_to_watch: list[str] = Field(description="追蹤指標", default_factory=list)


class CreativeExperiment(BaseModel):
    """素材相關實驗建議"""

    name: str = Field(description="實驗名稱")
    hypothesis: str = Field(description="假設說明")
    variations: list[str] = Field(description="測試變體內容", default_factory=list)
    primary_metric: str = Field(description="主要觀察指標")
    duration_days: Optional[int] = Field(default=None, description="建議觀察天數")


class CreativeSummary(BaseModel):
    """整體摘要"""

    top_creatives: list[CreativeMetric]
    low_creatives: list[CreativeMetric]
    key_findings: list[str]
    fatigue_signals: list[str] = Field(default_factory=list)


class CreativeAnalysisResult(BaseModel):
    """素材成效分析結果"""

    summary: CreativeSummary
    insights: list[CreativeInsight]
    optimizations: list[OptimizationIdea]
    experiments: list[CreativeExperiment]


@dataclass
class CreativePerformanceDeps:
    df: pd.DataFrame
    group_column: str = '行銷活動名稱'
    rag_service: Optional[object] = None


class CreativePerformanceAgent:
    """素材成效分析 Agent"""

    def __init__(self) -> None:
        model_name = os.getenv('OPENAI_MODEL', 'gpt-5-nano')
        self.agent = Agent(
            f'openai:{model_name}',
            output_type=CreativeAnalysisResult,
            deps_type=CreativePerformanceDeps,
            system_prompt=self._get_system_prompt(),
        )
        self._register_tools()

    def _get_system_prompt(self) -> str:
        return """
你是專業的 Meta 廣告創意分析師，擅長從數據找出高表現素材與優化方向。

分析原則：
1. 以數據為基礎，指出高效素材特徵與低效原因
2. 優化建議需具體可執行（包含步驟與追蹤指標）
3. 規劃實驗方案驗證假設
4. 如可取得歷史案例，可適度引用

輸出需符合 `CreativeAnalysisResult` 結構，使用繁體中文。
"""

    def _register_tools(self) -> None:
        @self.agent.tool
        def summarize_creatives(ctx: RunContext[CreativePerformanceDeps]) -> dict:
            df = ctx.deps.df
            metrics = []
            if 'headline' in df.columns:
                grouped = df.groupby('headline', dropna=True).agg({
                    '購買 ROAS（廣告投資報酬率）': 'mean',
                    'CTR（全部）': 'mean',
                    '每次購買的成本': 'mean' if '每次購買的成本' in df else 'mean',
                    '購買次數': 'sum',
                    '曝光次數': 'sum',
                    '花費金額 (TWD)': 'sum'
                }).reset_index()
                for _, row in grouped.iterrows():
                    metrics.append({
                        'name': 'Headline',
                        'value': row['headline'],
                        'roas': float(row['購買 ROAS（廣告投資報酬率）']),
                        'ctr': float(row['CTR（全部）'] * 100),
                        'cpa': float(row['每次購買的成本']) if '每次購買的成本' in row else None,
                        'conversions': float(row['購買次數']),
                        'impressions': float(row['曝光次數']),
                        'spend': float(row['花費金額 (TWD)'])
                    })
            return {'creative_metrics': metrics}

        @self.agent.tool
        def fetch_segment_performance(ctx: RunContext[CreativePerformanceDeps]) -> dict:
            df = ctx.deps.df
            if ctx.deps.group_column not in df.columns:
                return {'segments': []}
            grouped = df.groupby(ctx.deps.group_column, as_index=False).agg({
                '購買 ROAS（廣告投資報酬率）': 'mean',
                'CTR（全部）': 'mean',
                '花費金額 (TWD)': 'sum',
                '購買次數': 'sum'
            }).sort_values('花費金額 (TWD)', ascending=False).head(10)
            segments = []
            for _, row in grouped.iterrows():
                segments.append({
                    'segment': row[ctx.deps.group_column],
                    'roas': float(row['購買 ROAS（廣告投資報酬率）']),
                    'ctr': float(row['CTR（全部)'] * 100) if 'CTR（全部）' in row else None,
                    'spend': float(row['花費金額 (TWD)']),
                    'conversions': float(row['購買次數'])
                })
            return {'segments': segments}

        @self.agent.tool
        def load_rag_examples(ctx: RunContext[CreativePerformanceDeps]) -> dict:
            rag = ctx.deps.rag_service
            if not rag:
                return {'available': False}
            try:
                docs = rag.search_similar_ads('素材 成效 優化', top_k=3)
                results = []
                for doc in docs:
                    results.append({
                        'content': getattr(doc, 'page_content', ''),
                        'metadata': getattr(doc, 'metadata', {})
                    })
                return {'available': True, 'examples': results}
            except Exception:
                return {'available': False}

    async def analyze(
        self,
        df: pd.DataFrame,
        group_column: str = '行銷活動名稱',
        rag_service: Optional[object] = None,
    ) -> CreativeAnalysisResult:
        deps = CreativePerformanceDeps(
            df=df,
            group_column=group_column,
            rag_service=rag_service,
        )
        prompt = """
請整合工具取得的素材指標，輸出以下內容：
1. 最佳與需改善的素材摘要（指標、曝光、轉換）
2. 重要洞察與素材疲勞警訊
3. 優化建議（至少 3 條，含優先級、步驟、追蹤指標）
4. 2-3 個素材實驗方案

請使用繁體中文。
"""
        result = await self.agent.run(prompt, deps=deps)
        return result.output

    def analyze_sync(
        self,
        df: pd.DataFrame,
        group_column: str = '行銷活動名稱',
        rag_service: Optional[object] = None,
    ) -> CreativeAnalysisResult:
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.analyze(df, group_column=group_column, rag_service=rag_service)
        )
