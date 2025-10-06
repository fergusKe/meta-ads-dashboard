"""
即時優化建議 Agent (Pydantic AI)

功能：
- 根據最新數據盤點帳戶健康度
- 識別高優先級問題與成長機會
- 產出預算調整與實驗計畫
- 可選擇整合 RAG 歷史案例作為增強

特色：
- 完全型別安全
- 結構化輸出，方便 UI 呈現
- 依賴注入數據與閾值參數
- 工具函式負責前置分析，LLM 專注策略綜整
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import pandas as pd
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext


# ============================================
# 結構化輸出定義（完全型別安全）
# ============================================


class OptimizationAction(BaseModel):
    """單一優化建議/行動項目"""

    title: str = Field(description="建議標題")
    description: str = Field(description="建議詳述與背景")
    priority: str = Field(description="優先級標記（🔴/🟡/🟢 或類似文字）")
    impact: str = Field(description="預期影響或改善幅度說明")
    metric: str = Field(description="主要對應的 KPI")
    campaigns: list[str] = Field(description="受影響或建議操作的活動/廣告", default_factory=list)
    recommended_steps: list[str] = Field(description="建議執行步驟", default_factory=list)


class BudgetRecommendation(BaseModel):
    """預算調整建議"""

    campaign: str = Field(description="廣告活動/組合名稱")
    current_spend: float = Field(description="目前花費")
    recommended_spend: float = Field(description="建議花費")
    delta: float = Field(description="與目前相比的差異金額")
    action: str = Field(description="調整方向（增加/減少/重新分配等）")
    rationale: str = Field(description="調整理由")
    priority: str = Field(description="優先級")


class ExperimentPlan(BaseModel):
    """A/B 或實驗計畫"""

    name: str = Field(description="實驗名稱")
    hypothesis: str = Field(description="假設說明")
    metric: str = Field(description="主要觀察指標")
    variations: list[str] = Field(description="實驗變體內容")
    expected_outcome: str = Field(description="預期成效")


class OptimizationSummary(BaseModel):
    """總結與重點"""

    health_score: int = Field(ge=0, le=100, description="帳戶健康分數")
    overall_status: str = Field(description="整體狀態描述")
    key_insights: list[str] = Field(description="重要洞察與觀察")
    focus_areas: list[str] = Field(description="近期應聚焦的領域")
    next_steps: list[str] = Field(description="建議下一步行動")


class OptimizationResult(BaseModel):
    """整體優化結果"""

    summary: OptimizationSummary
    urgent_actions: list[OptimizationAction]
    opportunities: list[OptimizationAction]
    budget_recommendations: list[BudgetRecommendation]
    experiment_plan: list[ExperimentPlan]
    watchlist: list[str] = Field(description="需持續關注的指標/活動", default_factory=list)


# ============================================
# Agent 依賴注入
# ============================================


@dataclass
class OptimizationDeps:
    """OptimizationAgent 所需依賴"""

    df: pd.DataFrame
    target_roas: float
    max_cpa: float
    min_daily_budget: float
    rag_service: Optional[object] = None


# ============================================
# Agent 定義
# ============================================


class OptimizationAgent:
    """即時優化建議 Agent（Pydantic AI）"""

    def __init__(self) -> None:
        model_name = os.getenv("OPENAI_MODEL", "gpt-5-nano")
        self.agent = Agent(
            f"openai:{model_name}",
            output_type=OptimizationResult,
            deps_type=OptimizationDeps,
            system_prompt=self._get_system_prompt(),
        )
        self._register_tools()

    # ---------------------- 私有方法 ----------------------

    def _get_system_prompt(self) -> str:
        return """
你是一位專業的 Meta 廣告優化顧問，擅長根據廣告帳戶最新數據提供即時優化建議。

工作原則：
1. 先盤點帳戶健康度與關鍵指標
2. 優先指出高風險或需立即處理的項目
3. 找出具體且可執行的優化機會
4. 針對預算進行重新分配建議
5. 規劃可執行的實驗方案與待觀察項目

你的輸出必須完全符合 `OptimizationResult` 的結構，並確保：
- 建議內容具體、可執行，並包含關鍵指標與影響
- 優先級標記清楚（例如：🔴 高 / 🟡 中 / 🟢 低）
- 任何金額或指標都要以數據為依據，必要時可四捨五入處理
- 如果沒有適用資料，也要提供建議的替代做法或觀察指標

若有使用 RAG 取得歷史案例，請在描述中自然引用「歷史案例」或「知識庫洞察」。
"""

    def _register_tools(self) -> None:
        """註冊 Agent 可使用的工具"""

        @self.agent.tool
        def compute_account_snapshot(ctx: RunContext[OptimizationDeps]) -> dict:
            """計算帳戶整體指標快照"""

            df = ctx.deps.df
            if df.empty:
                return {"empty": True}

            roas_col = '購買 ROAS（廣告投資報酬率）'
            cpa_col = '每次購買的成本'
            spend_col = '花費金額 (TWD)'
            purchase_col = '購買次數'

            snapshot = {
                'avg_roas': float(df[roas_col].mean()) if roas_col in df else None,
                'median_roas': float(df[roas_col].median()) if roas_col in df else None,
                'avg_cpa': float(df[cpa_col].mean()) if cpa_col in df else None,
                'total_spend': float(df[spend_col].sum()) if spend_col in df else None,
                'total_purchases': float(df[purchase_col].sum()) if purchase_col in df else None,
                'campaign_count': int(df['行銷活動名稱'].nunique()) if '行銷活動名稱' in df else None,
                'date_range': _calc_date_range(df)
            }
            return snapshot

        @self.agent.tool
        def identify_urgent(ctx: RunContext[OptimizationDeps]) -> dict:
            """找出需立即處理的活動"""

            df = ctx.deps.df
            target_roas = ctx.deps.target_roas
            max_cpa = ctx.deps.max_cpa
            spend_col = '花費金額 (TWD)'

            if df.empty or '行銷活動名稱' not in df:
                return {'urgent_campaigns': []}

            grouped = df.groupby('行銷活動名稱', as_index=False).agg({
                '購買 ROAS（廣告投資報酬率）': 'mean',
                '每次購買的成本': 'mean',
                spend_col: 'sum',
                '觸及人數': 'sum'
            }).rename(columns={
                '購買 ROAS（廣告投資報酬率）': 'roas',
                '每次購買的成本': 'cpa',
            })

            urgent = []
            for _, row in grouped.iterrows():
                reasons = []
                if pd.notna(row['roas']) and row['roas'] < target_roas * 0.6:
                    reasons.append('ROAS 遠低於目標')
                if pd.notna(row['cpa']) and row['cpa'] > max_cpa * 1.2:
                    reasons.append('CPA 高於上限')
                if not reasons:
                    continue

                urgent.append({
                    'campaign': row['行銷活動名稱'],
                    'roas': float(row['roas']) if pd.notna(row['roas']) else None,
                    'cpa': float(row['cpa']) if pd.notna(row['cpa']) else None,
                    'spend': float(row[spend_col]) if pd.notna(row[spend_col]) else None,
                    'reasons': reasons
                })

            urgent_sorted = sorted(urgent, key=lambda x: x.get('spend', 0), reverse=True)[:8]
            return {'urgent_campaigns': urgent_sorted}

        @self.agent.tool
        def discover_opportunities(ctx: RunContext[OptimizationDeps]) -> dict:
            """挖掘成長機會"""

            df = ctx.deps.df
            if df.empty or '行銷活動名稱' not in df:
                return {'growth_candidates': []}

            grouped = df.groupby('行銷活動名稱', as_index=False).agg({
                '購買 ROAS（廣告投資報酬率）': 'mean',
                '每次購買的成本': 'mean',
                '花費金額 (TWD)': 'sum',
                '觸及人數': 'sum',
                '廣告組合名稱': 'nunique'
            }).rename(columns={'廣告組合名稱': 'adset_count'})

            benchmark_roas = grouped['購買 ROAS（廣告投資報酬率）'].median() if '購買 ROAS（廣告投資報酬率）' in grouped else None

            growth = []
            for _, row in grouped.iterrows():
                roas = row.get('購買 ROAS（廣告投資報酬率）')
                spend = row.get('花費金額 (TWD)')
                reach = row.get('觸及人數')
                if pd.isna(roas) or pd.isna(spend):
                    continue

                if roas >= ctx.deps.target_roas and spend < ctx.deps.min_daily_budget * 5:
                    growth.append({
                        'campaign': row['行銷活動名稱'],
                        'roas': float(roas),
                        'spend': float(spend),
                        'reach': float(reach) if pd.notna(reach) else None,
                        'adset_count': int(row.get('adset_count', 0)),
                        'benchmark_roas': float(benchmark_roas) if benchmark_roas is not None else None
                    })

            return {'growth_candidates': growth[:8]}

        @self.agent.tool
        def analyze_budget(ctx: RunContext[OptimizationDeps]) -> dict:
            """分析預算配置與再分配機會"""

            df = ctx.deps.df
            if df.empty or '行銷活動名稱' not in df:
                return {'budget_view': []}

            grouped = df.groupby('行銷活動名稱', as_index=False).agg({
                '花費金額 (TWD)': 'sum',
                '購買 ROAS（廣告投資報酬率）': 'mean'
            }).rename(columns={'花費金額 (TWD)': 'spend', '購買 ROAS（廣告投資報酬率）': 'roas'})

            budget_view = []
            for _, row in grouped.iterrows():
                budget_view.append({
                    'campaign': row['行銷活動名稱'],
                    'spend': float(row['spend']) if pd.notna(row['spend']) else 0.0,
                    'roas': float(row['roas']) if pd.notna(row['roas']) else None
                })

            budget_view.sort(key=lambda x: x['spend'], reverse=True)
            return {'budget_view': budget_view[:15]}

        @self.agent.tool
        def load_rag_insights(ctx: RunContext[OptimizationDeps]) -> dict:
            """從 RAG 取得歷史案例洞察（如可用）"""

            rag_service = ctx.deps.rag_service
            if not rag_service:
                return {'available': False}

            try:
                results = rag_service.search_similar_ads("預算優化 成長 活動".strip(), top_k=3)
                insights = []
                for doc in results:
                    insights.append({
                        'metadata': getattr(doc, 'metadata', {}),
                        'content': getattr(doc, 'page_content', '')[:400]
                    })
                return {'available': True, 'insights': insights}
            except Exception as exc:  # pragma: no cover - RAG 例外
                return {'available': False, 'error': str(exc)}

    # ---------------------- 對外方法 ----------------------

    async def optimize(
        self,
        df: pd.DataFrame,
        target_roas: float,
        max_cpa: float,
        min_daily_budget: float,
        rag_service: Optional[object] = None,
    ) -> OptimizationResult:
        """執行即時優化分析 (async)"""

        deps = OptimizationDeps(
            df=df,
            target_roas=target_roas,
            max_cpa=max_cpa,
            min_daily_budget=min_daily_budget,
            rag_service=rag_service,
        )

        user_prompt = f"""
請根據提供的廣告數據與分析工具輸出即時優化建議。

設定參數：
- 目標 ROAS：{target_roas:.2f}
- 可接受最大 CPA：{max_cpa:.2f} TWD
- 最小日預算：{min_daily_budget:.0f} TWD

請使用可用工具取得：
1. 帳戶整體指標快照
2. 高優先級問題活動 (urgent)
3. 具成長潛力的活動 (opportunities)
4. 預算重新分配觀察
5. RAG 歷史案例洞察（若 available=True）

輸出時務必填滿 `OptimizationResult` 所有欄位，並依據優先級與影響條理化。
"""

        result = await self.agent.run(user_prompt, deps=deps)
        return result.output

    def optimize_sync(
        self,
        df: pd.DataFrame,
        target_roas: float,
        max_cpa: float,
        min_daily_budget: float,
        rag_service: Optional[object] = None,
    ) -> OptimizationResult:
        """同步版本的優化分析（提供給 Streamlit 使用）"""

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
                max_cpa=max_cpa,
                min_daily_budget=min_daily_budget,
                rag_service=rag_service,
            )
        )


# ============================================
# 工具函式
# ============================================


def _calc_date_range(df: pd.DataFrame) -> Optional[str]:
    """計算資料的日期範圍（如有開始/結束欄位）"""

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
    except Exception:  # pragma: no cover - 容錯
        return None
