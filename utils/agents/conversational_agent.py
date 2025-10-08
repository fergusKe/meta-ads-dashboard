"""
對話式廣告投放助手 Agent (Pydantic AI)

功能：
- 自然語言對話
- 理解投手意圖
- 自動調用相關工具
- 整合 RAG 檢索
- 記憶上下文

特色：
- 多輪對話支持
- 整合現有 RAG 服務
- 自動選擇合適工具
- 結構化輸出
"""

import os

from pydantic_ai import Agent, RunContext
from pydantic import BaseModel, Field
from dataclasses import dataclass
from typing import Optional, Literal
import pandas as pd
from utils.rag_service import RAGService

# ============================================
# 結構化輸出定義
# ============================================

class AgentResponse(BaseModel):
    """Agent 回應（結構化）"""
    message: str = Field(description="給用戶的回應訊息")
    action_taken: Optional[str] = Field(
        default=None,
        description="Agent 執行的動作"
    )
    data: Optional[dict] = Field(
        default=None,
        description="相關數據（如果有）"
    )
    suggestions: list[str] = Field(
        default_factory=list,
        description="後續建議"
    )
    intent: Literal[
        "query_data",      # 查詢數據
        "analyze",         # 分析表現
        "recommend",       # 提供建議
        "generate_copy",   # 生成文案
        "optimize",        # 優化建議
        "chat"            # 一般對話
    ] = Field(description="識別的用戶意圖")


# ============================================
# Agent 依賴注入
# ============================================

@dataclass
class ConversationalDeps:
    """對話 Agent 依賴"""
    df: pd.DataFrame
    rag_service: Optional[RAGService] = None
    conversation_history: list[dict] = None


# ============================================
# 對話式 Agent
# ============================================

class ConversationalAdAgent:
    """對話式廣告投放助手（Pydantic AI）"""

    def __init__(self):
        """初始化 Agent"""
        # 從 .env 讀取模型名稱
        model_name = os.getenv('OPENAI_MODEL', 'gpt-5-nano')

        self.agent = Agent(
            f'openai:{model_name}',
            output_type=AgentResponse,
            deps_type=ConversationalDeps,
            system_prompt=self._get_system_prompt()
        )

        self._register_tools()

        # 對話歷史
        self.conversation_history = []

    def _get_system_prompt(self) -> str:
        """系統提示詞"""
        return """
你是專業的廣告投放助手 Agent，名字叫「小廣」。

職責：
1. 理解投手的需求（用自然語言）
2. 自動調用相關工具獲取數據
3. 分析並提供建議
4. 生成廣告文案（如果需要）
5. 記住對話上下文

你的特點：
- 友善、專業、有效率
- 主動提供建議
- 數據驅動決策
- 給出具體可執行的建議

對話風格：
- 簡潔明瞭（不要冗長）
- 使用表情符號增加親和力
- 重點用粗體標記
- 提供 2-3 個後續建議

重要：
- 總是基於實際數據回答
- 如果不確定，就調用工具查詢
- 提供的建議要具體可執行
"""

    def _register_tools(self):
        """註冊工具"""

        @self.agent.tool
        def query_campaign(ctx: RunContext[ConversationalDeps], campaign_name: str) -> dict:
            """查詢特定活動的表現"""
            df = ctx.deps.df

            campaign_data = df[df['行銷活動名稱'].str.contains(campaign_name, case=False, na=False)]

            if campaign_data.empty:
                return {"error": f"找不到活動: {campaign_name}"}

            return {
                "campaign_name": campaign_name,
                "spend": float(campaign_data['花費金額 (TWD)'].sum()),
                "roas": float(campaign_data['購買 ROAS（廣告投資報酬率）'].mean()),
                "purchases": int(campaign_data['購買次數'].sum()),
                "ctr": float(campaign_data['CTR（全部）'].mean()),
                "cpa": float(campaign_data['每次購買的成本'].mean())
            }

        @self.agent.tool
        def get_top_campaigns(ctx: RunContext[ConversationalDeps], limit: int = 5) -> list[dict]:
            """獲取表現最好的活動"""
            df = ctx.deps.df

            campaigns = df.groupby('行銷活動名稱').agg({
                '花費金額 (TWD)': 'sum',
                '購買 ROAS（廣告投資報酬率）': 'mean',
                '購買次數': 'sum'
            }).reset_index()

            top = campaigns.nlargest(limit, '購買 ROAS（廣告投資報酬率）')

            result = []
            for _, row in top.iterrows():
                result.append({
                    'campaign': row['行銷活動名稱'],
                    'roas': float(row['購買 ROAS（廣告投資報酬率）']),
                    'spend': float(row['花費金額 (TWD)']),
                    'purchases': int(row['購買次數'])
                })

            return result

        @self.agent.tool
        def search_similar_ads(ctx: RunContext[ConversationalDeps], query: str, k: int = 3) -> list[str]:
            """使用 RAG 搜尋相似的高效廣告"""
            rag = ctx.deps.rag_service

            if not rag:
                return ["RAG 服務未啟用，請先建立知識庫"]

            try:
                if not rag.load_knowledge_base("ad_creatives"):
                    return ["知識庫尚未建立"]

                results = rag.search_similar_ads(query, k=k)

                similar_ads = []
                for doc in results:
                    similar_ads.append(
                        f"ROAS {doc.metadata.get('roas', 0):.2f} - "
                        f"標題: {doc.metadata.get('headline', '未知')[:50]}"
                    )

                return similar_ads

            except Exception as e:
                return [f"搜尋失敗: {str(e)}"]

        @self.agent.tool
        def get_overall_summary(ctx: RunContext[ConversationalDeps]) -> dict:
            """獲取整體投放摘要"""
            df = ctx.deps.df

            return {
                "total_campaigns": df['行銷活動名稱'].nunique(),
                "total_spend": float(df['花費金額 (TWD)'].sum()),
                "total_purchases": int(df['購買次數'].sum()),
                "average_roas": float(df['購買 ROAS（廣告投資報酬率）'].mean()),
                "average_ctr": float(df['CTR（全部）'].mean())
            }

    async def chat(
        self,
        user_message: str,
        df: pd.DataFrame,
        rag_service: Optional[RAGService] = None
    ) -> AgentResponse:
        """
        對話（異步）

        Args:
            user_message: 用戶訊息
            df: 廣告數據
            rag_service: RAG 服務（可選）

        Returns:
            AgentResponse: 結構化回應
        """
        # 準備依賴
        deps = ConversationalDeps(
            df=df,
            rag_service=rag_service,
            conversation_history=self.conversation_history.copy()
        )

        # 添加用戶訊息到歷史
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        # 執行 Agent
        result = await self.agent.run(user_message, deps=deps)

        # 添加 Agent 回應到歷史
        self.conversation_history.append({
            "role": "assistant",
            "content": result.output.message
        })

        # 限制歷史長度（保留最近 10 輪對話）
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]

        return result.output

    def chat_sync(
        self,
        user_message: str,
        df: pd.DataFrame,
        rag_service: Optional[RAGService] = None
    ) -> AgentResponse:
        """
        對話（同步版本，用於 Streamlit）

        Args:
            user_message: 用戶訊息
            df: 廣告數據
            rag_service: RAG 服務（可選）

        Returns:
            AgentResponse: 結構化回應
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.chat(user_message, df, rag_service)
        )

    def clear_history(self):
        """清除對話歷史"""
        self.conversation_history = []


# ============================================
# 使用範例
# ============================================

if __name__ == "__main__":
    """測試對話 Agent"""
    from utils.data_loader import load_meta_ads_data

    # 載入數據
    df = load_meta_ads_data()

    # 載入 RAG
    rag = RAGService()
    try:
        rag.load_knowledge_base("ad_creatives")
        print("✅ RAG 知識庫已載入")
    except:
        print("⚠️ RAG 知識庫未建立")
        rag = None

    # 創建 Agent
    agent = ConversationalAdAgent()

    # 模擬對話
    print("\n🤖 小廣: 您好！我是廣告投放助手小廣，有什麼可以幫您的嗎？\n")

    # 範例對話
    queries = [
        "目前整體投放表現如何？",
        "幫我分析表現最好的前 3 個活動",
        "有沒有高 CTR 的廣告文案參考？"
    ]

    for query in queries:
        print(f"👤 用戶: {query}")

        response = agent.chat_sync(query, df, rag)

        print(f"🤖 小廣: {response.message}")

        if response.suggestions:
            print(f"💡 建議: {', '.join(response.suggestions)}")

        print(f"📊 意圖: {response.intent}\n")
