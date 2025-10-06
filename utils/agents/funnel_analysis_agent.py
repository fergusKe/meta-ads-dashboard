"""
轉換漏斗分析 Agent (Pydantic AI)

功能：
- 基於帳戶數據計算主要漏斗階段的轉換率與流失率
- 識別不同維度（例如裝置、地域、受眾）的瓶頸區段
- 生成動作清單與實驗建議，協助提升整體轉換效率
- 可選整合 RAG 歷史案例，提供更多實務洞察

特色：
- 完全型別安全、結構化輸出
- 工具負責運算指標及分群分析，LLM 專注於洞察整合
- 適合在 Streamlit UI 中直接呈現
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import pandas as pd
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

# ============================================
# 結構化輸出定義
# ============================================


class FunnelStage(BaseModel):
    """單一漏斗階段指標"""

    name: str = Field(description="階段名稱")
    count: float = Field(description="該階段人數或次數")
    conversion_rate: float = Field(description="相對於前一階段的轉換率 (%)")
    drop_rate: float = Field(description="與前一階段相比的流失率 (%)")
    benchmark: Optional[float] = Field(default=None, description="比較基準 (如整體平均)")
    note: Optional[str] = Field(default=None, description="補充說明")


class SegmentInsight(BaseModel):
    """分群洞察結果"""

    segment_name: str = Field(description="分群名稱，如：裝置/受眾")
    best_stage: str = Field(description="表現最佳的階段")
    best_stage_metric: float = Field(description="最佳階段指標")
    worst_stage: str = Field(description="需要優化的階段")
    worst_stage_metric: float = Field(description="該階段指標")
    opportunities: list[str] = Field(description="建議行動或洞察", default_factory=list)


class FunnelAction(BaseModel):
    """具體優化建議"""

    priority: str = Field(description="優先級（🔴/🟡/🟢）")
    title: str = Field(description="建議標題")
    description: str = Field(description="建議詳述")
    target_stage: str = Field(description="對應的漏斗階段")
    expected_impact: str = Field(description="預期影響")
    kpis: list[str] = Field(description="需要追蹤的指標", default_factory=list)
    steps: list[str] = Field(description="具體執行步驟", default_factory=list)


class ExperimentSuggestion(BaseModel):
    """A/B 或實驗建議"""

    name: str = Field(description="實驗名稱")
    hypothesis: str = Field(description="假設說明")
    metric: str = Field(description="主要觀察指標")
    audience: Optional[str] = Field(default=None, description="適用受眾")
    duration_days: Optional[int] = Field(default=None, description="建議實驗天數")
    expected_result: Optional[str] = Field(default=None, description="預期結果")


class FunnelSummary(BaseModel):
    """總結資訊"""

    overall_conversion_rate: float = Field(description="觸及到購買的總轉換率 (%)")
    main_bottleneck: str = Field(description="主要瓶頸階段")
    health_score: int = Field(ge=0, le=100, description="漏斗健康度")
    key_findings: list[str] = Field(description="重點發現", default_factory=list)
    watch_metrics: list[str] = Field(description="建議持續觀察的指標", default_factory=list)


class FunnelAnalysisResult(BaseModel):
    """漏斗分析總結果"""

    summary: FunnelSummary
    stages: list[FunnelStage]
    segment_insights: list[SegmentInsight]
    actions: list[FunnelAction]
    experiments: list[ExperimentSuggestion]


# ============================================
# 依賴注入定義
# ============================================


@dataclass
class FunnelAnalysisDeps:
    df: pd.DataFrame
    conversion_stage_columns: dict[str, str]
    # 例如 {'觸及': '觸及人數', '點擊': '連結點擊次數', '購買': '購買次數'}
    segment_columns: list[str]  # 可用於分群分析的欄位，如 ['裝置', '年齡']
    rag_service: Optional[object] = None


# ============================================
# Agent 定義
# ============================================


class FunnelAnalysisAgent:
    """轉換漏斗分析 Agent"""

    def __init__(self) -> None:
        model_name = os.getenv("OPENAI_MODEL", "gpt-5-nano")
        self.agent = Agent(
            f"openai:{model_name}",
            output_type=FunnelAnalysisResult,
            deps_type=FunnelAnalysisDeps,
            system_prompt=self._get_system_prompt(),
        )
        self._register_tools()

    def _get_system_prompt(self) -> str:
        return """
你是專業的 Meta 廣告轉換漏斗分析師，擅長從數據中識別瓶頸並提供可執行的優化建議。

分析原則：
1. 明確指出轉換率、流失率與健康度
2. 以資料驅動提出具體可執行的建議，並標記優先順序
3. 對不同分群給出差異化的策略方向
4. 規劃 A/B 測試與追蹤指標
5. 若可取得歷史案例，適度引用洞察

輸出必須符合 `FunnelAnalysisResult` 結構，並使用繁體中文。
"""

    def _register_tools(self) -> None:
        @self.agent.tool
        def compute_stages(ctx: RunContext[FunnelAnalysisDeps]) -> dict:
            df = ctx.deps.df
            stage_cols = ctx.deps.conversion_stage_columns
            stages = []
            prev_count = None

            for stage, col in stage_cols.items():
                if col not in df.columns:
                    continue
                count = float(df[col].sum())
                if prev_count is None:
                    conversion_rate = 100.0
                    drop_rate = 0.0
                else:
                    conversion_rate = (count / prev_count * 100) if prev_count else 0.0
                    drop_rate = 100 - conversion_rate
                stages.append({
                    'name': stage,
                    'count': count,
                    'conversion_rate': conversion_rate,
                    'drop_rate': drop_rate
                })
                prev_count = count

            return {'stages': stages}

        @self.agent.tool
        def analyze_segments(ctx: RunContext[FunnelAnalysisDeps]) -> dict:
            df = ctx.deps.df
            stage_cols = ctx.deps.conversion_stage_columns
            segment_cols = [col for col in ctx.deps.segment_columns if col in df.columns]

            insights = []
            for segment_col in segment_cols:
                top_groups = df[segment_col].value_counts().head(4).index.tolist()
                for group in top_groups:
                    group_df = df[df[segment_col] == group]
                    stage_metrics = {}
                    prev_count = None
                    for stage, col in stage_cols.items():
                        if col not in group_df.columns:
                            continue
                        count = float(group_df[col].sum())
                        if prev_count is None:
                            stage_metrics[stage] = 100.0
                        else:
                            stage_metrics[stage] = (count / prev_count * 100) if prev_count else 0.0
                        prev_count = count

                    if stage_metrics:
                        sorted_stages = sorted(stage_metrics.items(), key=lambda item: item[1], reverse=True)
                        best_stage, best_value = sorted_stages[0]
                        worst_stage, worst_value = sorted(sorted_stages, key=lambda item: item[1])[0]
                        insights.append({
                            'segment_name': f"{segment_col}：{group}",
                            'best_stage': best_stage,
                            'best_stage_metric': best_value,
                            'worst_stage': worst_stage,
                            'worst_stage_metric': worst_value,
                        })

            return {'segment_insights': insights}

        @self.agent.tool
        def load_rag_examples(ctx: RunContext[FunnelAnalysisDeps]) -> dict:
            rag_service = ctx.deps.rag_service
            if not rag_service:
                return {'available': False}
            try:
                docs = rag_service.search_similar_ads("轉換漏斗 優化 案例", top_k=3)
                formatted = []
                for doc in docs:
                    formatted.append({
                        'content': getattr(doc, 'page_content', ''),
                        'metadata': getattr(doc, 'metadata', {})
                    })
                return {'available': True, 'examples': formatted}
            except Exception:  # pragma: no cover - 容錯
                return {'available': False}

    # ---------------------- 對外方法 ----------------------

    async def analyze(
        self,
        df: pd.DataFrame,
        conversion_stage_columns: dict[str, str],
        segment_columns: list[str],
        rag_service: Optional[object] = None,
    ) -> FunnelAnalysisResult:
        deps = FunnelAnalysisDeps(
            df=df,
            conversion_stage_columns=conversion_stage_columns,
            segment_columns=segment_columns,
            rag_service=rag_service,
        )

        user_prompt = """
請分析提供的轉換漏斗資料，依據工具輸出計算的指標產生以下結果：
1. 整體健康度與主要瓶頸
2. 各階段的轉換率、流失率摘要
3. 針對重要分群（如裝置、年齡、地域等）的差異分析
4. 優先排序的行動建議（至少 3 條），每條須含優先級、指標、執行步驟
5. 2-3 個可立即執行的實驗或測試方案
6. 建議持續追蹤的指標/事件

請以繁體中文回答並套用 `FunnelAnalysisResult` 結構。
"""

        result = await self.agent.run(user_prompt, deps=deps)
        return result.output

    def analyze_sync(
        self,
        df: pd.DataFrame,
        conversion_stage_columns: dict[str, str],
        segment_columns: list[str],
        rag_service: Optional[object] = None,
    ) -> FunnelAnalysisResult:
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.analyze(
                df=df,
                conversion_stage_columns=conversion_stage_columns,
                segment_columns=segment_columns,
                rag_service=rag_service,
            )
        )

