"""
Pydantic AI Agents for Meta Ads Dashboard

這個模組包含所有使用 Pydantic AI 開發的智能 Agent
- 完全型別安全
- 內建可觀測性（Logfire）
- 與現有 LangChain RAG 共存

架構：
- LangChain + ChromaDB: RAG 層（檢索增強生成）
- Pydantic AI: Agent 層（自主決策和執行）
"""

from .daily_check_agent import DailyCheckAgent, DailyCheckResult
from .conversational_agent import ConversationalAdAgent, AgentResponse

__all__ = [
    # 每日巡檢 Agent
    'DailyCheckAgent',
    'DailyCheckResult',

    # 對話式 Agent
    'ConversationalAdAgent',
    'AgentResponse',
]
