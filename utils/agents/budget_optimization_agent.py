"""
預算優化建議 Agent (Pydantic AI)

功能：
- 盤點廣告帳戶整體預算效益與高低表現活動
- 建議增加、減少或重新分配預算的具體動作
- 提供實驗方案與追蹤指標，協助持續驗證
- 可選擇整合 RAG 歷史案例作為補充洞察

特色：
- 完全型別安全，輸出 `BudgetOptimizationResult`
- 工具函式負責計算核心指標與分群摘要，LLM 專注策略整合
- 支援同步/非同步呼叫，方便 Streamlit 頁面使用
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import pandas as pd
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext


class BudgetSummary(BaseModel):
    """帳戶預算概況"""

    total_spend: float = Field(description="總花費 (TWD)")
    total_revenue: float = Field(description="總營收估計 (TWD)")
    overall_roas: float = Field(description="整體 ROAS")
    total_profit: float = Field(description="預估利潤 (TWD)")
    health_score: int = Field(ge=0, le=100, description="預算健康度")
    key_findings: list[str] = Field(description="重點洞察", default_factory=list)
    watch_metrics: list[str] = Field(description="建議追蹤指標", default_factory=list)


class BudgetAdjustment(BaseModel):
    """單一預算調整建議"""

    campaign: str = Field(description="活動/廣告組合名稱")
    current_spend: float = Field(description="目前花費")
    recommended_spend: float = Field(description="建議花費")
    delta: float = Field(description="花費差異")
    priority: str = Field(description="優先級（🔴/🟡/🟢 等）")
    rationale: str = Field(description="調整理由")
    expected_impact: str = Field(description="預期成效")


class GrowthOpportunity(BaseModel):
    """成長機會與再投資方向"""

    name: str = Field(description="活動/策略名稱")
    current_spend: float = Field(description="目前花費")
    current_roas: float = Field(description="目前 ROAS")
    recommendation: str = Field(description="建議措施")
    supporting_metrics: list[str] = Field(description="佐證指標", default_factory=list)


class BudgetExperiment(BaseModel):
    """預算相關 A/B 或測試方案"""

    name: str = Field(description="實驗名稱")
    hypothesis: str = Field(description="假設說明")
    metric: str = Field(description="預期觀察指標")
    budget_split: str = Field(description="預算分配策略")
    duration_days: Optional[int] = Field(default=None, description="建議觀察天數")
    expected_result: Optional[str] = Field(default=None, description="預期結果")


class AllocationPlan(BaseModel):
    """整體預算重分配方案摘要"""

    increase_amount: float = Field(description="建議增加總額")
    decrease_amount: float = Field(description="建議減少總額")
    reinvest_amount: float = Field(description="建議重新分配總額")
    notes: list[str] = Field(description="額外說明", default_factory=list)


class BudgetOptimizationResult(BaseModel):
    """預算優化建議輸出"""

    summary: BudgetSummary
    increase_recommendations: list[BudgetAdjustment] = Field(default_factory=list)
    decrease_recommendations: list[BudgetAdjustment] = Field(default_factory=list)
    reallocation_plan: AllocationPlan
    growth_opportunities: list[GrowthOpportunity] = Field(default_factory=list)
    experiments: list[BudgetExperiment] = Field(default_factory=list)


@dataclass
class BudgetOptimizationDeps:
    df: pd.DataFrame
    target_roas: float
    increase_threshold: float
    decrease_threshold: float
    rag_service: Optional[object] = None


class BudgetOptimizationAgent:
    """預算優化 Agent"""

    def __init__(self) -> None:
        model_name = os.getenv('OPENAI_MODEL', 'gpt-5-nano')
        self.agent = Agent(
            f'openai:{model_name}',
            output_type=BudgetOptimizationResult,
            deps_type=BudgetOptimizationDeps,
            system_prompt=self._get_system_prompt(),
        )
        self._register_tools()

    def _get_system_prompt(self) -> str:
        return """
你是 Meta 廣告預算優化專家，擅長根據帳戶數據提出具體可執行的預算策略。

分析原則：
1. 盤點整體帳戶預算健康度與重點指標
2. 找出需要增加、減少、重新分配的活動
3. 給出具體預算數字與優先順序，並說明理由
4. 規劃可驗證的實驗方案與追蹤指標
5. 若可取得歷史案例，可自然引用洞察

輸出必須符合 `BudgetOptimizationResult` 結構，並使用繁體中文，內容需要具體、可執行。
"""

    def _register_tools(self) -> None:
        @self.agent.tool
        def compute_summary(ctx: RunContext[BudgetOptimizationDeps]) -> dict:
            df = ctx.deps.df
            roas_col = '購買 ROAS（廣告投資報酬率）'
            spend_col = '花費金額 (TWD)'
            revenue = (df[spend_col] * df[roas_col]).sum() if roas_col in df and spend_col in df else 0.0
            spend = df[spend_col].sum() if spend_col in df else 0.0
            overall_roas = (revenue / spend) if spend else 0.0
            profit = revenue - spend
            return {
                'total_spend': float(spend),
                'total_revenue': float(revenue),
                'overall_roas': float(overall_roas),
                'total_profit': float(profit),
                'campaign_count': int(df['行銷活動名稱'].nunique()) if '行銷活動名稱' in df else 0,
            }

        @self.agent.tool
        def group_by_campaign(ctx: RunContext[BudgetOptimizationDeps]) -> dict:
            df = ctx.deps.df
            spend_col = '花費金額 (TWD)'
            roas_col = '購買 ROAS（廣告投資報酬率）'
            purchase_col = '購買次數'
            if spend_col not in df or roas_col not in df:
                return {'campaigns': []}
            grouped = df.groupby('行銷活動名稱', as_index=False).agg({
                spend_col: 'sum',
                roas_col: 'mean',
                purchase_col: 'sum' if purchase_col in df else 'mean',
            })
            campaigns = []
            for _, row in grouped.iterrows():
                campaigns.append({
                    'campaign': row['行銷活動名稱'],
                    'spend': float(row[spend_col]),
                    'roas': float(row[roas_col]),
                    'purchases': float(row[purchase_col]) if purchase_col in df else None,
                })
            return {'campaigns': campaigns}

        @self.agent.tool
        def detect_increase_targets(ctx: RunContext[BudgetOptimizationDeps]) -> dict:
            target = ctx.deps.target_roas
            df = ctx.deps.df
            spend_col = '花費金額 (TWD)'
            roas_col = '購買 ROAS（廣告投資報酬率）'
            if spend_col not in df or roas_col not in df:
                return {'increase': []}
            grouped = df.groupby('行銷活動名稱', as_index=False).agg({
                spend_col: 'mean',
                roas_col: 'mean'
            })
            low_spend = grouped[grouped[spend_col] < ctx.deps.increase_threshold]
            candidates = low_spend[low_spend[roas_col] >= target]
            increase = []
            for _, row in candidates.iterrows():
                increase.append({
                    'campaign': row['行銷活動名稱'],
                    'spend': float(row[spend_col]),
                    'roas': float(row[roas_col])
                })
            return {'increase': increase}

        @self.agent.tool
        def detect_decrease_targets(ctx: RunContext[BudgetOptimizationDeps]) -> dict:
            df = ctx.deps.df
            spend_col = '花費金額 (TWD)'
            roas_col = '購買 ROAS（廣告投資報酬率）'
            if spend_col not in df or roas_col not in df:
                return {'decrease': []}
            grouped = df.groupby('行銷活動名稱', as_index=False).agg({
                spend_col: 'mean',
                roas_col: 'mean'
            })
            high_spend = grouped[grouped[spend_col] >= ctx.deps.decrease_threshold]
            candidates = high_spend[high_spend[roas_col] < ctx.deps.target_roas * 0.6]
            decrease = []
            for _, row in candidates.iterrows():
                decrease.append({
                    'campaign': row['行銷活動名稱'],
                    'spend': float(row[spend_col]),
                    'roas': float(row[roas_col])
                })
            return {'decrease': decrease}

        @self.agent.tool
        def load_rag_examples(ctx: RunContext[BudgetOptimizationDeps]) -> dict:
            rag = ctx.deps.rag_service
            if not rag:
                return {'available': False}
            try:
                docs = rag.search_similar_ads('預算重新分配 成功 案例', top_k=3)
                results = []
                for doc in docs:
                    results.append({
                        'content': getattr(doc, 'page_content', ''),
                        'metadata': getattr(doc, 'metadata', {})
                    })
                return {'available': True, 'examples': results}
            except Exception:
                return {'available': False}

    async def optimize(
        self,
        df: pd.DataFrame,
        target_roas: float,
        increase_threshold: float,
        decrease_threshold: float,
        rag_service: Optional[object] = None,
    ) -> BudgetOptimizationResult:
        deps = BudgetOptimizationDeps(
            df=df,
            target_roas=target_roas,
            increase_threshold=increase_threshold,
            decrease_threshold=decrease_threshold,
            rag_service=rag_service,
        )
        user_prompt = f"""
請依據可用工具計算出的資料，輸出完整的預算優化建議：
- 帳戶概要（健康度、總花費、整體 ROAS、重點洞察）
- 應增加預算的活動（提供建議金額與理由）
- 應減少/重新分配預算的活動（提供建議金額與理由）
- 總體預算重分配方案摘要
- 成長機會與再投資方向
- 建議的預算相關實驗方案（至少 2 個）
- 需要持續追蹤的指標

目標 ROAS：{target_roas:.2f}
增加預算評估閾值（花費低於此值視為預算不足）：{increase_threshold:.0f} TWD
減少預算評估閾值（花費高於此值但效益不佳視為需調整）：{decrease_threshold:.0f} TWD
"""
        result = await self.agent.run(user_prompt, deps=deps)
        return result.output

    def optimize_sync(
        self,
        df: pd.DataFrame,
        target_roas: float,
        increase_threshold: float,
        decrease_threshold: float,
        rag_service: Optional[object] = None,
    ) -> BudgetOptimizationResult:
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.optimize(
                df=df,
                target_roas=target_roas,
                increase_threshold=increase_threshold,
                decrease_threshold=decrease_threshold,
                rag_service=rag_service,
            )
        )
