"""
素材優化 Agent (Pydantic AI)

功能：
- 分析現有素材表現
- 提供具體優化建議
- 生成 A/B 測試計畫
- 整合歷史數據洞察

特色：
- 完全型別安全
- 結構化輸出
- 數據驅動的建議
- 整合 RAG 知識庫
"""

import os

from pydantic_ai import Agent, RunContext
from pydantic import BaseModel, Field, field_validator
from dataclasses import dataclass
from typing import Optional
import pandas as pd

# ============================================
# 結構化輸出定義（完全型別安全）
# ============================================

class CreativeOptimization(BaseModel):
    """單個素材優化建議"""
    element_type: str = Field(
        description="素材元素類型（如：標題、圖片、文案、CTA）"
    )
    current_performance: str = Field(
        description="當前表現描述"
    )
    optimization_action: str = Field(
        description="具體優化動作"
    )
    expected_improvement: str = Field(
        description="預期改善效果"
    )
    priority: str = Field(
        description="優先級（🔴高/🟡中/🟢低）"
    )
    execution_steps: list[str] = Field(
        description="執行步驟",
        min_length=2,
        max_length=5
    )

class ABTestVariant(BaseModel):
    """A/B 測試變體"""
    variant_name: str = Field(description="變體名稱")
    changes: list[str] = Field(description="變更內容")
    hypothesis: str = Field(description="測試假設")
    expected_metric_impact: str = Field(description="預期指標影響")

class CreativeOptimizationResult(BaseModel):
    """素材優化結果（完全型別安全）"""
    optimizations: list[CreativeOptimization] = Field(
        description="優化建議列表",
        min_length=5,
        max_length=10
    )
    quick_wins: list[str] = Field(
        description="快速見效的改進（1-3天可完成）",
        min_length=3,
        max_length=5
    )
    long_term_strategy: str = Field(
        description="長期策略（1個月以上的素材規劃）"
    )
    ab_test_plan: list[ABTestVariant] = Field(
        description="A/B 測試計畫（3-5個測試方案）",
        min_length=3,
        max_length=5
    )
    performance_prediction: dict[str, str] = Field(
        description="表現預測（預期哪些優化效果最好）",
        default_factory=dict
    )
    resource_requirements: dict[str, str] = Field(
        description="資源需求（時間、人力、預算）",
        default_factory=dict
    )
    risk_assessment: dict[str, str] = Field(
        description="風險評估（可能的風險和應對方案）",
        default_factory=dict
    )

    @field_validator("performance_prediction", "resource_requirements", "risk_assessment", mode="before")
    @classmethod
    def _ensure_dict(cls, value: object) -> dict[str, str]:
        if value is None or value == "":
            return {}
        if isinstance(value, dict):
            return value
        return {"summary": str(value)}

# ============================================
# Agent 依賴注入
# ============================================

@dataclass
class CreativeOptimizationDeps:
    """Agent 依賴（用於依賴注入）"""
    df: pd.DataFrame  # 廣告數據
    brand_name: str = "耘初茶食"
    current_avg_roas: float = 0.0
    current_avg_ctr: float = 0.0
    target_roas: float = 3.0
    focus_area: Optional[str] = None  # 重點優化領域
    rag_service: Optional[object] = None  # RAG 服務

# ============================================
# Agent 定義
# ============================================

class CreativeOptimizationAgent:
    """素材優化 Agent（Pydantic AI）"""

    def __init__(self):
        """初始化 Agent"""
        # 從 .env 讀取模型名稱
        model_name = os.getenv('OPENAI_MODEL', 'gpt-5-nano')

        # 創建 Agent
        self.agent = Agent(
            f'openai:{model_name}',
            output_type=CreativeOptimizationResult,
            deps_type=CreativeOptimizationDeps,
            system_prompt=self._get_system_prompt()
        )

        # 註冊工具
        self._register_tools()

    def _get_system_prompt(self) -> str:
        """系統提示詞"""
        return """
你是專業的廣告素材優化 AI Agent，專精於 Meta 廣告創意優化。

專長：
1. 分析素材表現數據
2. 識別優化機會
3. 設計 A/B 測試方案
4. 提供可執行的改善計畫

優化框架：

**素材元素分類**：
1. **文案元素**：
   - 標題（Headline）
   - 主文案（Primary Text）
   - 描述（Description）
   - CTA 按鈕文字

2. **視覺元素**：
   - 主圖片/影片
   - 色彩配置
   - 構圖和佈局
   - 品牌元素

3. **策略元素**：
   - 訊息定位
   - 情感訴求
   - 價值主張
   - 差異化點

**優化原則**：

1. **數據驅動**：
   - 基於實際表現數據
   - 對比高效/低效素材
   - 找出成功模式

2. **快速迭代**：
   - 優先快速見效的改進
   - 設計簡單易測試的變體
   - 持續優化循環

3. **系統性思考**：
   - 不只改單一元素
   - 考慮元素間的配合
   - 整體策略一致性

4. **風險管理**：
   - 評估改動風險
   - 提供備案方案
   - 漸進式推出

**A/B 測試設計**：
- 單變因測試（控制變數）
- 明確假設和成功指標
- 足夠樣本數和測試時間
- 統計顯著性驗證

輸出要求：
- 5-10 個具體優化建議
- 3-5 個快速見效的改進
- 長期策略規劃
- 3-5 個 A/B 測試方案
- 表現預測
- 資源需求評估
- 風險評估

建議格式：
- 優先級標記清楚（🔴高/🟡中/🟢低）
- 執行步驟具體可行
- 預期效果可量化
- 考慮資源限制
"""

    def _register_tools(self):
        """註冊 Agent 可用的工具"""

        @self.agent.tool
        def analyze_creative_performance(ctx: RunContext[CreativeOptimizationDeps]) -> dict:
            """分析素材表現"""
            df = ctx.deps.df

            # 計算平均指標
            avg_roas = df['購買 ROAS（廣告投資報酬率）'].mean()
            avg_ctr = df['CTR（全部）'].mean()
            avg_cpa = df['每次購買的成本'].mean()

            # 找出高效和低效素材
            high_performers = df[df['購買 ROAS（廣告投資報酬率）'] > avg_roas * 1.5]
            low_performers = df[df['購買 ROAS（廣告投資報酬率）'] < avg_roas * 0.5]

            return {
                'overall_metrics': {
                    'avg_roas': float(avg_roas),
                    'avg_ctr': float(avg_ctr),
                    'avg_cpa': float(avg_cpa),
                    'total_campaigns': df['行銷活動名稱'].nunique()
                },
                'high_performers_count': len(high_performers),
                'low_performers_count': len(low_performers),
                'performance_distribution': {
                    'excellent': len(df[df['購買 ROAS（廣告投資報酬率）'] > 5]),
                    'good': len(df[(df['購買 ROAS（廣告投資報酬率）'] >= 3) & (df['購買 ROAS（廣告投資報酬率）'] < 5)]),
                    'average': len(df[(df['購買 ROAS（廣告投資報酬率）'] >= 1.5) & (df['購買 ROAS（廣告投資報酬率）'] < 3)]),
                    'poor': len(df[df['購買 ROAS（廣告投資報酬率）'] < 1.5])
                }
            }

        @self.agent.tool
        def get_successful_creative_patterns(ctx: RunContext[CreativeOptimizationDeps]) -> dict:
            """找出成功素材的共同模式"""
            df = ctx.deps.df

            # 找出表現最好的廣告
            top_performers = df.nlargest(10, '購買 ROAS（廣告投資報酬率）')

            # 分析共同特徵
            patterns = {
                'top_campaigns': top_performers['行銷活動名稱'].tolist(),
                'common_audiences': top_performers['目標'].value_counts().head(3).to_dict() if '目標' in df.columns else {},
                'avg_top_roas': float(top_performers['購買 ROAS（廣告投資報酬率）'].mean()),
                'avg_top_ctr': float(top_performers['CTR（全部）'].mean()),
            }

            # 提取活動名稱中的關鍵字
            campaign_names = ' '.join(top_performers['行銷活動名稱'].astype(str).tolist())
            common_keywords = []
            keywords = ['茶', '健康', '養生', '傳統', '手作', '精選', '好茶', '新品', '限時']
            for keyword in keywords:
                if keyword in campaign_names:
                    common_keywords.append(keyword)

            patterns['common_keywords'] = common_keywords

            return patterns

        @self.agent.tool
        def identify_underperforming_elements(ctx: RunContext[CreativeOptimizationDeps]) -> dict:
            """識別表現不佳的素材元素"""
            df = ctx.deps.df
            target_roas = ctx.deps.target_roas

            # 找出低於目標的廣告
            underperformers = df[df['購買 ROAS（廣告投資報酬率）'] < target_roas]

            if len(underperformers) == 0:
                return {'message': '所有廣告都達到目標 ROAS'}

            issues = {
                'low_roas_campaigns': underperformers.nlargest(10, '花費金額 (TWD)')['行銷活動名稱'].tolist(),
                'avg_underperformer_roas': float(underperformers['購買 ROAS（廣告投資報酬率）'].mean()),
                'total_wasted_spend': float(underperformers['花費金額 (TWD)'].sum()),
                'common_issues': []
            }

            # 分析常見問題
            if underperformers['CTR（全部）'].mean() < df['CTR（全部）'].mean():
                issues['common_issues'].append('CTR 偏低：素材吸引力不足')

            if underperformers['每次購買的成本'].mean() > df['每次購買的成本'].mean() * 1.5:
                issues['common_issues'].append('CPA 過高：轉換效率低')

            return issues

        @self.agent.tool
        def get_optimization_examples(ctx: RunContext[CreativeOptimizationDeps]) -> dict:
            """從 RAG 知識庫獲取優化範例（如果可用）"""
            rag_service = ctx.deps.rag_service

            if rag_service:
                try:
                    # 檢索相似的優化案例
                    similar_ads = rag_service.search_similar_ads(
                        "素材優化 A/B測試 提升轉換",
                        top_k=5
                    )
                    return {
                        'similar_optimization_cases': similar_ads,
                        'insights': '已從知識庫檢索相似優化案例'
                    }
                except:
                    pass

            # 如果沒有 RAG，返回一般最佳實踐
            return {
                'best_practices': [
                    '標題測試：問句 vs 陳述句',
                    '圖片測試：產品特寫 vs 生活場景',
                    'CTA 測試：立即購買 vs 了解更多',
                    '文案測試：功能性 vs 情感性',
                    '色彩測試：暖色調 vs 冷色調'
                ]
            }

        @self.agent.tool
        def calculate_optimization_potential(ctx: RunContext[CreativeOptimizationDeps]) -> dict:
            """計算優化潛力"""
            df = ctx.deps.df
            current_avg_roas = df['購買 ROAS（廣告投資報酬率）'].mean()
            target_roas = ctx.deps.target_roas
            total_spend = df['花費金額 (TWD)'].sum()

            # 如果所有預算都達到目標 ROAS 可以獲得的營收
            current_revenue = (df['花費金額 (TWD)'] * df['購買 ROAS（廣告投資報酬率）']).sum()
            potential_revenue = total_spend * target_roas

            revenue_gap = potential_revenue - current_revenue
            improvement_percentage = (revenue_gap / current_revenue * 100) if current_revenue > 0 else 0

            return {
                'current_avg_roas': float(current_avg_roas),
                'target_roas': float(target_roas),
                'total_spend': float(total_spend),
                'current_revenue': float(current_revenue),
                'potential_revenue': float(potential_revenue),
                'revenue_gap': float(revenue_gap),
                'improvement_percentage': float(improvement_percentage)
            }

    async def optimize_creative(
        self,
        df: pd.DataFrame,
        target_roas: float = 3.0,
        focus_area: Optional[str] = None,
        rag_service: Optional[object] = None
    ) -> CreativeOptimizationResult:
        """
        生成素材優化建議

        Args:
            df: 廣告數據 DataFrame
            target_roas: 目標 ROAS
            focus_area: 重點優化領域（可選）
            rag_service: RAG 服務（可選）

        Returns:
            CreativeOptimizationResult: 型別安全的優化建議
        """
        # 計算當前指標
        current_avg_roas = df['購買 ROAS（廣告投資報酬率）'].mean()
        current_avg_ctr = df['CTR（全部）'].mean()

        # 準備依賴
        deps = CreativeOptimizationDeps(
            df=df,
            current_avg_roas=current_avg_roas,
            current_avg_ctr=current_avg_ctr,
            target_roas=target_roas,
            focus_area=focus_area,
            rag_service=rag_service
        )

        # 構建提示詞
        user_prompt = f"""
執行素材優化分析：

當前表現：
- 平均 ROAS：{current_avg_roas:.2f}
- 目標 ROAS：{target_roas:.2f}
- 平均 CTR：{current_avg_ctr:.3f}%

重點領域：{focus_area or '全面優化'}

請執行以下分析：
1. 使用工具分析整體素材表現
2. 找出成功素材的共同模式
3. 識別表現不佳的元素
4. 計算優化潛力
5. 檢索優化範例（如有 RAG）

請提供：
- 5-10 個具體優化建議（涵蓋文案、圖片、策略）
- 3-5 個快速見效的改進
- 長期素材策略（1個月規劃）
- 3-5 個 A/B 測試方案
- 表現預測（預期效果）
- 資源需求評估
- 風險評估

要求：
- 建議要基於數據分析
- 優先級要合理
- 執行步驟要具體
- 預期效果要可衡量
"""

        # 執行 Agent
        result = await self.agent.run(user_prompt, deps=deps)
        return result.output

    def optimize_creative_sync(
        self,
        df: pd.DataFrame,
        target_roas: float = 3.0,
        focus_area: Optional[str] = None,
        rag_service: Optional[object] = None
    ) -> CreativeOptimizationResult:
        """
        同步版本的素材優化（用於 Streamlit）
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.optimize_creative(df, target_roas, focus_area, rag_service)
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
    agent = CreativeOptimizationAgent()

    # 生成優化建議
    result = agent.optimize_creative_sync(
        df,
        target_roas=3.0,
        focus_area="提升圖片素材吸引力"
    )

    # 輸出結果
    print("=" * 70)
    print("素材優化建議：")
    for i, opt in enumerate(result.optimizations, 1):
        print(f"\n{i}. [{opt.priority}] {opt.element_type}")
        print(f"   當前表現：{opt.current_performance}")
        print(f"   優化動作：{opt.optimization_action}")
        print(f"   預期改善：{opt.expected_improvement}")

    print(f"\n{'='*70}")
    print("快速見效改進：")
    for i, quick_win in enumerate(result.quick_wins, 1):
        print(f"{i}. {quick_win}")

    print(f"\n{'='*70}")
    print("A/B 測試計畫：")
    for i, test in enumerate(result.ab_test_plan, 1):
        print(f"\n測試 {i}：{test.variant_name}")
        print(f"假設：{test.hypothesis}")
        print(f"變更：{', '.join(test.changes)}")
