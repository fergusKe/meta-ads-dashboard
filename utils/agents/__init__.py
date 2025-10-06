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

# Phase 1: 核心生成功能 Agents
from .copywriting_agent import CopywritingAgent, CopywritingResult
from .image_prompt_agent import ImagePromptAgent, ImageGenerationResult
from .image_analysis_agent import ImageAnalysisAgent, ImageAnalysisResult
from .creative_optimization_agent import CreativeOptimizationAgent, CreativeOptimizationResult
from .optimization_agent import OptimizationAgent, OptimizationResult
from .funnel_analysis_agent import FunnelAnalysisAgent, FunnelAnalysisResult
from .budget_optimization_agent import BudgetOptimizationAgent, BudgetOptimizationResult
from .creative_performance_agent import CreativePerformanceAgent, CreativeAnalysisResult
from .quality_score_agent import QualityScoreAgent, QualityAnalysisResult
from .audience_expansion_agent import AudienceExpansionAgent, AudienceExpansionResult
from .report_generation_agent import ReportGenerationAgent, ReportGenerationResult
from .ab_test_design_agent import ABTestDesignAgent, ABTestDesignResult
from .competitor_analysis_agent import CompetitorAnalysisAgent, CompetitorAnalysisResult
from .mvt_design_agent import MVTDesignAgent, MVTDesignResult
from .strategy_agent import StrategyAgent, StrategyAgentResult

# 已完成的 Agents
from .daily_check_agent import DailyCheckAgent, DailyCheckResult
from .conversational_agent import ConversationalAdAgent, AgentResponse

__all__ = [
    # Phase 1: 核心生成功能 Agents
    'CopywritingAgent',
    'CopywritingResult',
    'ImagePromptAgent',
    'ImageGenerationResult',
    'ImageAnalysisAgent',
    'ImageAnalysisResult',
    'OptimizationAgent',
    'OptimizationResult',
    'FunnelAnalysisAgent',
    'FunnelAnalysisResult',
    'BudgetOptimizationAgent',
    'BudgetOptimizationResult',
    'CreativePerformanceAgent',
    'CreativeAnalysisResult',
    'QualityScoreAgent',
    'QualityAnalysisResult',
    'AudienceExpansionAgent',
    'AudienceExpansionResult',
    'ReportGenerationAgent',
    'ReportGenerationResult',
    'ABTestDesignAgent',
    'ABTestDesignResult',
    'CompetitorAnalysisAgent',
    'CompetitorAnalysisResult',
    'MVTDesignAgent',
    'MVTDesignResult',
    'StrategyAgent',
    'StrategyAgentResult',
    'CreativeOptimizationAgent',
    'CreativeOptimizationResult',

    # 每日巡檢 Agent
    'DailyCheckAgent',
    'DailyCheckResult',

    # 對話式 Agent
    'ConversationalAdAgent',
    'AgentResponse',
]
