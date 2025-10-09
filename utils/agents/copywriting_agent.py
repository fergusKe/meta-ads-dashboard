"""
廣告文案生成 Agent (Pydantic AI)

功能：
- 生成多個廣告文案變體
- 結合品牌聲音和受眾洞察
- 提供 A/B 測試建議
- 整合 RAG 檢索高效文案範例

特色：
- 完全型別安全
- 結構化輸出（Pydantic models）
- 整合 RAG 知識庫
- 自動化文案優化
"""

from pydantic_ai import Agent, RunContext
from pydantic import BaseModel, Field
from dataclasses import dataclass
from typing import Optional
import pandas as pd
import os
import streamlit as st
from utils.cache_manager import cache_agent_result
from utils.error_handler import handle_agent_errors
from utils.model_selector import ModelSelector
from utils.history_manager import record_history
from utils.validators import validate_inputs
from utils.security import sanitize_payload

# ============================================
# 結構化輸出定義（完全型別安全）
# ============================================

class AdCopyVariant(BaseModel):
    """單個廣告文案變體"""
    headline: str = Field(description="廣告標題（25-40字）")
    primary_text: str = Field(description="主要文案（90-125字）")
    cta: str = Field(description="行動呼籲")
    tone: str = Field(description="語氣風格（如：專業、親切、活潑）")
    target_audience: str = Field(description="目標受眾描述")
    key_message: str = Field(description="核心訊息")
    emotional_appeal: str = Field(description="情感訴求點")
    differentiation: str = Field(description="差異化重點")

class CopywritingResult(BaseModel):
    """文案生成結果（完全型別安全）"""
    variants: list[AdCopyVariant] = Field(
        description="3-5個文案變體"
    )
    strategy_explanation: str = Field(
        description="整體策略說明（為何選擇這些角度）"
    )
    ab_test_suggestions: list[str] = Field(
        description="A/B 測試建議（測試哪些變因）"
    )
    optimization_tips: list[str] = Field(
        description="優化建議（如何進一步改善）"
    )
    performance_prediction: str = Field(
        description="預測表現說明，例如：'變體1因為情感訴求強烈可能點擊率最高，變體3因為價值主張明確可能轉換率最好'"
    )
    compliance_check: str = Field(
        description="合規性檢查結果，例如：'所有文案均符合 Meta 廣告政策，無誇大不實或針對個人特徵的內容'"
    )

# ============================================
# Agent 依賴注入
# ============================================

@dataclass
class CopywritingDeps:
    """Agent 依賴（用於依賴注入）"""
    df: pd.DataFrame  # 廣告數據
    brand_name: str = "耘初茶食"
    product_category: str = "台灣茶飲、茶食產品"
    brand_values: str = "傳統工藝與現代創新結合，注重健康養生"
    target_audience: Optional[str] = None
    campaign_objective: Optional[str] = None
    special_requirements: Optional[str] = None
    rag_service: Optional[object] = None  # RAG 服務（可選）

# ============================================
# Agent 定義
# ============================================

class CopywritingAgent:
    """廣告文案生成 Agent（Pydantic AI）"""

    def __init__(self):
        """初始化 Agent"""
        selector = ModelSelector()
        preference = st.session_state.get('user_preferences', {}).get('copywriting_complexity')
        model_name = selector.choose(complexity=preference or os.getenv('COPYWRITING_COMPLEXITY', 'balanced'))

        # 供 UI 顯示使用的實際模型名稱
        self.model_name = model_name

        self.agent = Agent(
            f'openai:{model_name}',
            output_type=CopywritingResult,
            deps_type=CopywritingDeps,
            system_prompt=self._get_system_prompt()
        )

        # 註冊工具
        self._register_tools()

    def _get_system_prompt(self) -> str:
        """系統提示詞"""
        return """
你是專業的 Meta 廣告文案創作 AI Agent。

專長：
1. 撰寫高轉換的廣告文案
2. 理解品牌聲音和目標受眾
3. 結合數據洞察優化文案
4. 設計 A/B 測試策略

文案原則：
- **吸引注意**：前 3 秒抓住眼球
- **情感連結**：喚起共鳴和購買慾望
- **清晰價值**：明確傳達產品價值
- **行動呼籲**：強力且具體的 CTA
- **品牌一致**：符合品牌調性和價值觀

Meta 廣告文案最佳實踐：
1. 標題要簡短有力（25-40字最佳）
2. 主文案要有故事性或情境感（90-125字）
3. 前 2-3 句最重要（決定是否繼續閱讀）
4. 使用具體數字和利益點
5. CTA 要明確且緊迫
6. 避免過度行銷用語（避免被系統降分）

輸出要求：
- 生成 3-5 個文案變體（不同角度和策略）
- 每個變體要有明確的受眾定位
- 提供 A/B 測試建議
- 預測哪個變體可能表現最好
- 檢查是否符合 Meta 廣告政策

Meta 廣告政策注意事項：
- ❌ 不能誇大效果（「一定」「保證」「100%」）
- ❌ 不能針對個人特徵（「你是不是很胖」）
- ❌ 不能製造不安全感（「你的健康出問題了」）
- ✅ 使用正面、包容性語言
- ✅ 提供實際價值和解決方案
"""

    def _register_tools(self):
        """註冊 Agent 可用的工具"""

        @self.agent.tool
        def get_top_performing_copy(ctx: RunContext[CopywritingDeps]) -> dict:
            """獲取高效文案範例（從歷史數據）"""
            df = ctx.deps.df

            # 篩選高 ROAS 的廣告
            high_performers = df[
                df['購買 ROAS（廣告投資報酬率）'] > 3.0
            ].nlargest(10, '購買 ROAS（廣告投資報酬率）')

            examples = []
            for _, row in high_performers.iterrows():
                if pd.notna(row.get('行銷活動名稱')):
                    examples.append({
                        'campaign_name': row['行銷活動名稱'],
                        'roas': float(row['購買 ROAS（廣告投資報酬率）']),
                        'ctr': float(row['CTR（全部）']),
                        'target_audience': row.get('年齡', '') + ' ' + row.get('性別', '')
                    })

            return {
                'high_performing_campaigns': examples,
                'common_themes': self._extract_common_themes(examples)
            }

        @self.agent.tool
        def get_audience_insights(ctx: RunContext[CopywritingDeps]) -> dict:
            """獲取受眾洞察"""
            df = ctx.deps.df

            # 分析不同受眾的表現
            if '年齡' in df.columns and '性別' in df.columns:
                audience_performance = df.groupby(['年齡', '性別']).agg({
                    '購買 ROAS（廣告投資報酬率）': 'mean',
                    'CTR（全部）': 'mean',
                    '購買次數': 'sum'
                }).round(2).to_dict()

                return {
                    'audience_performance': audience_performance,
                    'top_audiences': df.groupby(['年齡', '性別'])['購買 ROAS（廣告投資報酬率）'].mean().nlargest(5).to_dict()
                }

            return {'message': '無受眾數據可分析'}

        @self.agent.tool
        def get_brand_voice_guidelines(ctx: RunContext[CopywritingDeps]) -> dict:
            """獲取品牌語調指南"""
            return {
                'brand_name': ctx.deps.brand_name,
                'product_category': ctx.deps.product_category,
                'brand_values': ctx.deps.brand_values,
                'tone_examples': [
                    '溫暖親切、專業可信',
                    '強調傳統工藝與現代創新',
                    '重視健康養生',
                    '台灣在地品牌自豪感'
                ],
                'avoid': [
                    '過於商業化的推銷語言',
                    '浮誇不實的宣傳',
                    '缺乏溫度的機械式文案'
                ]
            }

        @self.agent.tool
        def analyze_competitor_messaging(ctx: RunContext[CopywritingDeps]) -> dict:
            """分析競品訊息（使用 RAG 如果可用）"""
            rag_service = ctx.deps.rag_service

            if rag_service:
                # 使用 RAG 檢索相似的高效文案
                try:
                    similar_ads = rag_service.search_similar_ads(
                        "茶飲 健康 養生 傳統",
                        top_k=5
                    )
                    return {
                        'similar_high_performing_ads': similar_ads,
                        'messaging_insights': '已從知識庫檢索相似高效廣告'
                    }
                except:
                    pass

            return {
                'market_positioning': '台灣茶飲市場',
                'differentiation_points': [
                    '傳統工藝與現代創新',
                    '健康養生訴求',
                    '高品質茶葉',
                    '在地品牌'
                ]
            }

        @self.agent.tool
        def get_seasonal_themes(ctx: RunContext[CopywritingDeps]) -> dict:
            """獲取當季主題建議"""
            import datetime
            month = datetime.datetime.now().month

            seasonal_themes = {
                (3, 4, 5): {
                    'season': '春季',
                    'themes': ['春茶上市', '清新爽口', '春日養生', '新品嚐鮮'],
                    'emotions': ['清新', '活力', '期待']
                },
                (6, 7, 8): {
                    'season': '夏季',
                    'themes': ['消暑解渴', '冰涼茶飲', '夏日清涼', '午後時光'],
                    'emotions': ['清涼', '舒爽', '放鬆']
                },
                (9, 10, 11): {
                    'season': '秋季',
                    'themes': ['秋季養生', '溫潤茶香', '秋收好茶', '品茗時刻'],
                    'emotions': ['溫暖', '沉靜', '豐收']
                },
                (12, 1, 2): {
                    'season': '冬季',
                    'themes': ['暖心熱飲', '冬日養生', '溫暖時光', '節慶送禮'],
                    'emotions': ['溫暖', '療癒', '關懷']
                }
            }

            for months, theme_data in seasonal_themes.items():
                if month in months:
                    return theme_data

            return {'season': '全年', 'themes': ['品質茶飲', '健康養生']}

    def _extract_common_themes(self, campaigns: list[dict]) -> list[str]:
        """提取共同主題（簡單關鍵字分析）"""
        common_keywords = []
        campaign_names = [c.get('campaign_name', '') for c in campaigns]

        # 常見茶飲相關關鍵字
        keywords = ['茶', '健康', '養生', '傳統', '手作', '精選', '好茶', '品質', '新鮮']

        for keyword in keywords:
            if sum(keyword in name for name in campaign_names) >= 2:
                common_keywords.append(keyword)

        return common_keywords if common_keywords else ['品質', '健康']

    @cache_agent_result()
    @handle_agent_errors(context='生成文案')
    async def generate_copy(
        self,
        df: pd.DataFrame,
        target_audience: Optional[str] = None,
        campaign_objective: Optional[str] = None,
        special_requirements: Optional[str] = None,
        rag_service: Optional[object] = None
    ) -> CopywritingResult:
        """
        生成廣告文案

        Args:
            df: 廣告數據 DataFrame
            target_audience: 目標受眾描述
            campaign_objective: 廣告目標
            special_requirements: 特殊要求
            rag_service: RAG 服務（可選）

        Returns:
            CopywritingResult: 型別安全的文案生成結果
        """
        warnings = validate_inputs({
            'target_audience': target_audience,
            'objective': campaign_objective,
        })
        if warnings:
            for message in warnings:
                st.warning(f'輸入提醒: {message}')

        deps = CopywritingDeps(
            df=df,
            target_audience=target_audience,
            campaign_objective=campaign_objective,
            special_requirements=special_requirements,
            rag_service=rag_service
        )

        # 構建提示詞
        user_prompt = f"""
生成廣告文案：

目標受眾：{target_audience or '一般大眾'}
廣告目標：{campaign_objective or '提升品牌知名度與購買轉換'}
特殊要求：{special_requirements or '無'}

請執行以下步驟：
1. 使用工具了解歷史高效文案
2. 分析目標受眾特徵
3. 參考品牌語調指南
4. 考慮當季主題
5. 生成 3-5 個不同角度的文案變體

文案要求：
- 每個變體要有不同的情感訴求或角度
- 標題要吸引人、引發好奇
- 主文案要有故事感或情境描述
- CTA 要明確且具吸引力
- 符合 Meta 廣告政策

請提供：
- 3-5 個完整文案變體
- 整體策略說明
- A/B 測試建議
- 優化建議
- 預測表現
- 合規性檢查
"""

        # 執行 Agent
        result = await self.agent.run(user_prompt, deps=deps)
        output = result.output
        record_history(
            'CopywritingAgent',
            inputs=sanitize_payload({
                'target_audience': target_audience or '',
                'campaign_objective': campaign_objective or '',
                'special_requirements': special_requirements or '',
            }),
            output=output.model_dump() if hasattr(output, 'model_dump') else str(output),
            metadata={'warnings': warnings},
        )
        return output

    def generate_copy_sync(
        self,
        df: pd.DataFrame,
        target_audience: Optional[str] = None,
        campaign_objective: Optional[str] = None,
        special_requirements: Optional[str] = None,
        rag_service: Optional[object] = None
    ) -> CopywritingResult:
        """
        同步版本的文案生成（用於 Streamlit）

        Args:
            df: 廣告數據 DataFrame
            target_audience: 目標受眾描述
            campaign_objective: 廣告目標
            special_requirements: 特殊要求
            rag_service: RAG 服務（可選）

        Returns:
            CopywritingResult: 型別安全的文案生成結果
        """
        import asyncio

        # 在新的 event loop 中執行
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.generate_copy(
                df,
                target_audience,
                campaign_objective,
                special_requirements,
                rag_service
            )
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
    agent = CopywritingAgent()

    # 生成文案
    result = agent.generate_copy_sync(
        df,
        target_audience="25-44歲 女性，注重健康養生",
        campaign_objective="推廣新品茶飲，提升購買轉換",
        special_requirements="強調天然無添加，適合下午茶時光"
    )

    # 輸出結果（完全型別安全）
    print("=" * 50)
    print("文案變體：")
    for i, variant in enumerate(result.variants, 1):
        print(f"\n變體 {i}:")
        print(f"標題：{variant.headline}")
        print(f"文案：{variant.primary_text}")
        print(f"CTA：{variant.cta}")
        print(f"語氣：{variant.tone}")
        print(f"核心訊息：{variant.key_message}")

    print("\n" + "=" * 50)
    print("策略說明：")
    print(result.strategy_explanation)

    print("\n" + "=" * 50)
    print("A/B 測試建議：")
    for suggestion in result.ab_test_suggestions:
        print(f"- {suggestion}")
