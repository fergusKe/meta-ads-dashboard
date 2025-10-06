"""
每日廣告巡檢 Agent (Pydantic AI)

功能：
- 自動檢查所有廣告活動
- 識別問題活動（低 ROAS、高花費）
- 提供優化建議
- 計算風險金額

特色：
- 完全型別安全
- 結構化輸出（Pydantic models）
- 可觀測性（Logfire）
- 整合現有 RAG 服務
"""

from pydantic_ai import Agent, RunContext
from pydantic import BaseModel, Field
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import pandas as pd
import os

# 可選：整合 Logfire（需要 API key）
try:
    import logfire
    LOGFIRE_AVAILABLE = True
except:
    LOGFIRE_AVAILABLE = False


# ============================================
# 結構化輸出定義（完全型別安全）
# ============================================

class ProblemCampaign(BaseModel):
    """問題活動"""
    campaign_name: str = Field(description="活動名稱")
    roas: float = Field(description="當前 ROAS")
    spend: float = Field(description="花費金額（TWD）")
    purchases: int = Field(description="購買次數")
    issue_type: str = Field(description="問題類型")
    severity: str = Field(description="嚴重程度：高/中/低")
    root_cause: str = Field(description="根本原因分析")

class Recommendation(BaseModel):
    """優化建議"""
    action: str = Field(description="建議動作")
    target: str = Field(description="針對哪個活動/受眾/素材")
    priority: str = Field(description="優先級：🔴高/🟡中/🟢低")
    expected_impact: str = Field(description="預期效果")
    execution_steps: list[str] = Field(description="執行步驟")

class DailyCheckResult(BaseModel):
    """每日檢查結果（完全型別安全）"""
    check_date: str = Field(description="檢查日期")
    total_campaigns: int = Field(description="總活動數")
    total_spend: float = Field(description="總花費")
    average_roas: float = Field(description="平均 ROAS")

    problem_campaigns: list[ProblemCampaign] = Field(
        default_factory=list,
        description="問題活動列表"
    )
    urgent_issues: list[str] = Field(
        default_factory=list,
        description="緊急問題清單"
    )
    recommendations: list[Recommendation] = Field(
        default_factory=list,
        description="優化建議"
    )

    estimated_risk_amount: float = Field(
        default=0.0,
        description="估計風險金額（持續投放可能浪費的預算）"
    )

    health_score: int = Field(
        ge=0,
        le=100,
        description="整體健康分數 0-100"
    )

    summary: str = Field(description="執行摘要（給主管看）")


# ============================================
# Agent 依賴注入（FastAPI 風格）
# ============================================

@dataclass
class DailyCheckDeps:
    """Agent 依賴（用於依賴注入）"""
    df: pd.DataFrame
    target_roas: float = 3.0
    max_acceptable_cpa: float = 500.0
    min_campaign_spend: float = 1000.0  # 只檢查花費超過此金額的活動


# ============================================
# Agent 定義
# ============================================

class DailyCheckAgent:
    """每日巡檢 Agent（Pydantic AI）"""

    def __init__(self):
        """初始化 Agent"""
        # 從 .env 讀取模型名稱
        model_name = os.getenv('OPENAI_MODEL', 'gpt-5-nano')

        # 創建 Agent
        self.agent = Agent(
            f'openai:{model_name}',
            output_type=DailyCheckResult,
            deps_type=DailyCheckDeps,
            system_prompt=self._get_system_prompt()
        )

        # 註冊工具
        self._register_tools()

    def _get_system_prompt(self) -> str:
        """系統提示詞"""
        return """
你是專業的 Meta 廣告監控 Agent。

職責：
1. 檢查所有廣告活動的表現
2. 識別問題活動（低 ROAS、高花費、低轉換）
3. 分析根本原因
4. 提供具體可執行的優化建議
5. 評估風險金額

要求：
- 數據驅動，基於實際數據分析
- 建議要具體可執行（不要泛泛而談）
- 優先處理高花費低效活動（風險最大）
- 提供 3-5 個最重要的建議即可
- 執行摘要要簡潔有力（3-5 句話）

輸出格式：
- 使用結構化的 Pydantic 模型
- 確保所有欄位都有意義的值
- 優先級標記要準確
"""

    def _register_tools(self):
        """註冊 Agent 可用的工具"""

        @self.agent.tool
        def get_all_campaigns_summary(ctx: RunContext[DailyCheckDeps]) -> dict:
            """獲取所有活動的摘要數據"""
            df = ctx.deps.df

            summary = {
                "total_campaigns": df['行銷活動名稱'].nunique(),
                "total_spend": float(df['花費金額 (TWD)'].sum()),
                "total_purchases": int(df['購買次數'].sum()),
                "average_roas": float(df['購買 ROAS（廣告投資報酬率）'].mean()),
                "average_ctr": float(df['CTR（全部）'].mean()),
                "date_range": {
                    "start": str(df['開始'].min()),
                    "end": str(df['開始'].max())
                }
            }

            return summary

        @self.agent.tool
        def get_campaign_performance(ctx: RunContext[DailyCheckDeps], limit: int = 50) -> list[dict]:
            """獲取活動表現詳情"""
            df = ctx.deps.df

            # 按活動分組
            campaigns = df.groupby('行銷活動名稱').agg({
                '花費金額 (TWD)': 'sum',
                '購買 ROAS（廣告投資報酬率）': 'mean',
                '購買次數': 'sum',
                'CTR（全部）': 'mean',
                '每次購買的成本': 'mean',
                '連結點擊次數': 'sum'
            }).reset_index()

            # 計算轉換率
            campaigns['轉換率'] = (
                campaigns['購買次數'] / campaigns['連結點擊次數'] * 100
            ).fillna(0)

            # 轉換為字典列表
            result = []
            for _, row in campaigns.head(limit).iterrows():
                result.append({
                    'campaign_name': row['行銷活動名稱'],
                    'spend': float(row['花費金額 (TWD)']),
                    'roas': float(row['購買 ROAS（廣告投資報酬率）']),
                    'purchases': int(row['購買次數']),
                    'ctr': float(row['CTR（全部）']),
                    'cpa': float(row['每次購買的成本']),
                    'conversion_rate': float(row['轉換率'])
                })

            return result

        @self.agent.tool
        def identify_low_roas_campaigns(ctx: RunContext[DailyCheckDeps]) -> list[dict]:
            """識別低 ROAS 活動"""
            df = ctx.deps.df
            target_roas = ctx.deps.target_roas
            min_spend = ctx.deps.min_campaign_spend

            # 分組並篩選
            campaigns = df.groupby('行銷活動名稱').agg({
                '花費金額 (TWD)': 'sum',
                '購買 ROAS（廣告投資報酬率）': 'mean',
                '購買次數': 'sum',
                'CTR（全部）': 'mean',
                '每次購買的成本': 'mean'
            }).reset_index()

            # 找出問題活動
            problems = campaigns[
                (campaigns['購買 ROAS（廣告投資報酬率）'] < target_roas) &
                (campaigns['花費金額 (TWD)'] >= min_spend)
            ].sort_values('花費金額 (TWD)', ascending=False)

            result = []
            for _, row in problems.iterrows():
                result.append({
                    'campaign_name': row['行銷活動名稱'],
                    'roas': float(row['購買 ROAS（廣告投資報酬率）']),
                    'spend': float(row['花費金額 (TWD)']),
                    'purchases': int(row['購買次數']),
                    'ctr': float(row['CTR（全部）']),
                    'cpa': float(row['每次購買的成本']),
                    'gap_to_target': float(target_roas - row['購買 ROAS（廣告投資報酬率）'])
                })

            return result

        @self.agent.tool
        def calculate_risk_amount(ctx: RunContext[DailyCheckDeps]) -> dict:
            """計算風險金額（低效活動持續投放的浪費）"""
            df = ctx.deps.df
            target_roas = ctx.deps.target_roas

            # 找出低 ROAS 活動
            low_roas = df[df['購買 ROAS（廣告投資報酬率）'] < target_roas]

            # 計算這些活動的總花費
            total_low_roas_spend = low_roas['花費金額 (TWD)'].sum()

            # 估算浪費（假設這些預算能達到目標 ROAS 可以獲得的額外營收）
            current_revenue = (
                low_roas['花費金額 (TWD)'] *
                low_roas['購買 ROAS（廣告投資報酬率）']
            ).sum()

            potential_revenue = total_low_roas_spend * target_roas

            waste = potential_revenue - current_revenue

            return {
                'total_low_roas_spend': float(total_low_roas_spend),
                'current_revenue': float(current_revenue),
                'potential_revenue': float(potential_revenue),
                'estimated_waste': float(waste),
                'percentage_of_total': float(
                    total_low_roas_spend / df['花費金額 (TWD)'].sum() * 100
                ) if df['花費金額 (TWD)'].sum() > 0 else 0
            }

    async def run_daily_check(
        self,
        df: pd.DataFrame,
        target_roas: float = 3.0,
        max_cpa: float = 500.0
    ) -> DailyCheckResult:
        """
        執行每日檢查

        Args:
            df: 廣告數據 DataFrame
            target_roas: 目標 ROAS
            max_cpa: 最大可接受 CPA

        Returns:
            DailyCheckResult: 型別安全的檢查結果
        """
        # 準備依賴
        deps = DailyCheckDeps(
            df=df,
            target_roas=target_roas,
            max_acceptable_cpa=max_cpa
        )

        # 執行 Agent
        if LOGFIRE_AVAILABLE:
            with logfire.span('daily_ad_check'):
                result = await self.agent.run(
                    f"""
                    執行每日廣告巡檢：

                    目標：
                    1. 檢查所有活動表現
                    2. 識別問題活動（ROAS < {target_roas}，花費 >= 1000）
                    3. 分析根本原因（受眾？素材？預算？）
                    4. 提供 3-5 個最重要的優化建議
                    5. 計算風險金額
                    6. 評估整體健康分數（0-100）

                    請使用提供的工具獲取數據，然後生成完整的檢查報告。
                    """,
                    deps=deps
                )
        else:
            result = await self.agent.run(
                f"""
                執行每日廣告巡檢：

                目標：
                1. 檢查所有活動表現
                2. 識別問題活動（ROAS < {target_roas}，花費 >= 1000）
                3. 分析根本原因（受眾？素材？預算？）
                4. 提供 3-5 個最重要的優化建議
                5. 計算風險金額
                6. 評估整體健康分數（0-100）

                請使用提供的工具獲取數據，然後生成完整的檢查報告。
                """,
                deps=deps
            )

        return result.output

    def run_daily_check_sync(
        self,
        df: pd.DataFrame,
        target_roas: float = 3.0,
        max_cpa: float = 500.0
    ) -> DailyCheckResult:
        """
        同步版本的每日檢查（用於 Streamlit）

        Args:
            df: 廣告數據 DataFrame
            target_roas: 目標 ROAS
            max_cpa: 最大可接受 CPA

        Returns:
            DailyCheckResult: 型別安全的檢查結果
        """
        import asyncio

        # 在新的 event loop 中執行
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.run_daily_check(df, target_roas, max_cpa)
        )


# ============================================
# 使用範例
# ============================================

if __name__ == "__main__":
    """測試 Agent"""
    from utils.data_loader import load_meta_ads_data

    # 載入數據
    df = load_meta_ads_data()

    # 創建 Agent
    agent = DailyCheckAgent()

    # 執行檢查
    result = agent.run_daily_check_sync(df, target_roas=3.0)

    # 輸出結果（完全型別安全）
    print(f"檢查日期：{result.check_date}")
    print(f"總活動數：{result.total_campaigns}")
    print(f"問題活動：{len(result.problem_campaigns)}")
    print(f"健康分數：{result.health_score}/100")
    print(f"\n執行摘要：\n{result.summary}")

    # 顯示建議
    print(f"\n優化建議：")
    for rec in result.recommendations:
        print(f"- [{rec.priority}] {rec.action}")
