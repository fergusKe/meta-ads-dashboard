"""
統一錯誤處理與重試機制

功能：
- 自動重試失敗的 API 請求
- 統一錯誤訊息格式
- 智能退避策略（Exponential Backoff）
- 用戶友善的錯誤提示
- 詳細錯誤日誌記錄

使用範例：
    from utils.error_handler import handle_agent_errors

    @handle_agent_errors(max_retries=3, backoff_factor=2)
    async def generate_copy(self, ...):
        # Agent 執行邏輯
        ...
"""

import os
import time
import traceback
from functools import wraps
from typing import Optional, Callable, Any
from datetime import datetime
import streamlit as st


class AgentError(Exception):
    """Agent 執行錯誤基類"""
    pass


class APIError(AgentError):
    """API 相關錯誤"""
    pass


class ValidationError(AgentError):
    """驗證錯誤"""
    pass


class TimeoutError(AgentError):
    """超時錯誤"""
    pass


class AgentErrorHandler:
    """統一錯誤處理器"""

    # 錯誤類型對應的用戶友善訊息
    ERROR_MESSAGES = {
        'RateLimitError': {
            'icon': '⏳',
            'title': 'API 配額限制',
            'message': '目前 API 請求次數已達上限，請稍後再試',
            'retry': True
        },
        'APIConnectionError': {
            'icon': '🔌',
            'title': '網路連線問題',
            'message': '無法連接到 AI 服務，請檢查網路連線',
            'retry': True
        },
        'APITimeoutError': {
            'icon': '⏱️',
            'title': '請求超時',
            'message': 'AI 服務回應時間過長，請重試',
            'retry': True
        },
        'AuthenticationError': {
            'icon': '🔑',
            'title': 'API 金鑰錯誤',
            'message': 'API 金鑰無效或已過期，請檢查設定',
            'retry': False
        },
        'InvalidRequestError': {
            'icon': '❌',
            'title': '請求參數錯誤',
            'message': '請求格式不正確，請檢查輸入參數',
            'retry': False
        },
        'ValidationError': {
            'icon': '⚠️',
            'title': '資料驗證失敗',
            'message': 'AI 輸出格式不符合預期，請重試',
            'retry': True
        },
        'UnknownError': {
            'icon': '🐛',
            'title': '未預期錯誤',
            'message': '發生未知錯誤，請聯繫技術支援',
            'retry': False
        }
    }

    @staticmethod
    def get_error_type(error: Exception) -> str:
        """
        判斷錯誤類型

        Args:
            error: 異常物件

        Returns:
            錯誤類型字串
        """
        error_class = error.__class__.__name__

        # 處理 OpenAI 錯誤
        if 'openai' in str(type(error).__module__):
            return error_class

        # 處理 Pydantic 驗證錯誤
        if 'pydantic' in str(type(error).__module__):
            return 'ValidationError'

        # 其他錯誤
        return 'UnknownError'

    @staticmethod
    def display_error(
        error: Exception,
        context: str = "",
        show_details: bool = True
    ) -> None:
        """
        顯示用戶友善的錯誤訊息

        Args:
            error: 異常物件
            context: 錯誤上下文（例如：「生成文案時」）
            show_details: 是否顯示詳細錯誤資訊
        """
        error_type = AgentErrorHandler.get_error_type(error)
        error_info = AgentErrorHandler.ERROR_MESSAGES.get(
            error_type,
            AgentErrorHandler.ERROR_MESSAGES['UnknownError']
        )

        # 顯示主要錯誤訊息
        error_title = f"{error_info['icon']} {error_info['title']}"
        if context:
            error_title = f"{error_title}（{context}）"

        st.error(f"**{error_title}**\n\n{error_info['message']}")

        # 顯示詳細資訊（可摺疊）
        if show_details:
            with st.expander("🔍 詳細錯誤資訊", expanded=False):
                st.code(f"錯誤類型: {error_type}\n錯誤訊息: {str(error)}")

                # 顯示完整 traceback
                with st.expander("📋 完整堆疊追蹤", expanded=False):
                    st.code(traceback.format_exc())

    @staticmethod
    def should_retry(error: Exception) -> bool:
        """
        判斷是否應該重試

        Args:
            error: 異常物件

        Returns:
            是否應該重試
        """
        error_type = AgentErrorHandler.get_error_type(error)
        error_info = AgentErrorHandler.ERROR_MESSAGES.get(
            error_type,
            AgentErrorHandler.ERROR_MESSAGES['UnknownError']
        )
        return error_info.get('retry', False)

    @staticmethod
    def calculate_backoff(attempt: int, backoff_factor: float = 2) -> float:
        """
        計算退避時間（Exponential Backoff）

        Args:
            attempt: 當前重試次數
            backoff_factor: 退避係數

        Returns:
            等待時間（秒）
        """
        # 第一次重試：backoff_factor^0 = 1 秒
        # 第二次重試：backoff_factor^1 = 2 秒
        # 第三次重試：backoff_factor^2 = 4 秒
        return backoff_factor ** (attempt - 1)


def handle_agent_errors(
    max_retries: int = 3,
    backoff_factor: float = 2,
    context: str = "",
    show_progress: bool = True
):
    """
    裝飾器：統一處理 Agent 執行錯誤並自動重試

    Args:
        max_retries: 最大重試次數
        backoff_factor: 退避係數（指數退避）
        context: 錯誤上下文描述
        show_progress: 是否顯示重試進度

    使用範例：
        @handle_agent_errors(max_retries=3, context="生成文案")
        async def generate_copy(self, ...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            last_error = None

            for attempt in range(1, max_retries + 1):
                try:
                    # 執行原始函數
                    result = await func(*args, **kwargs)
                    return result

                except Exception as error:
                    last_error = error
                    error_type = AgentErrorHandler.get_error_type(error)

                    # 判斷是否應該重試
                    should_retry = AgentErrorHandler.should_retry(error)

                    if attempt < max_retries and should_retry:
                        # 計算等待時間
                        wait_time = AgentErrorHandler.calculate_backoff(
                            attempt,
                            backoff_factor
                        )

                        # 顯示重試訊息
                        if show_progress:
                            retry_msg = f"⏳ 重試中... (第 {attempt}/{max_retries} 次，{wait_time:.1f} 秒後重試)"
                            st.warning(retry_msg)

                        # 等待
                        time.sleep(wait_time)

                        # 繼續下一次重試
                        continue
                    else:
                        # 不重試或已達最大重試次數
                        if attempt >= max_retries:
                            error_context = f"{context}（已重試 {max_retries} 次）" if context else f"已重試 {max_retries} 次"
                        else:
                            error_context = f"{context}（不可重試的錯誤）" if context else "不可重試的錯誤"

                        # 顯示錯誤
                        AgentErrorHandler.display_error(
                            error,
                            context=error_context,
                            show_details=True
                        )

                        # 拋出錯誤
                        raise

            # 理論上不會執行到這裡
            if last_error:
                raise last_error

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            """同步版本的錯誤處理"""
            last_error = None

            for attempt in range(1, max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    return result

                except Exception as error:
                    last_error = error
                    should_retry = AgentErrorHandler.should_retry(error)

                    if attempt < max_retries and should_retry:
                        wait_time = AgentErrorHandler.calculate_backoff(
                            attempt,
                            backoff_factor
                        )

                        if show_progress:
                            st.warning(f"⏳ 重試中... (第 {attempt}/{max_retries} 次，{wait_time:.1f} 秒後重試)")

                        time.sleep(wait_time)
                        continue
                    else:
                        if attempt >= max_retries:
                            error_context = f"{context}（已重試 {max_retries} 次）" if context else f"已重試 {max_retries} 次"
                        else:
                            error_context = f"{context}（不可重試的錯誤）" if context else "不可重試的錯誤"

                        AgentErrorHandler.display_error(
                            error,
                            context=error_context,
                            show_details=True
                        )
                        raise

            if last_error:
                raise last_error

        # 根據函數類型返回對應的 wrapper
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# 便捷函數
def display_error(error: Exception, context: str = "") -> None:
    """
    顯示錯誤訊息（便捷函數）

    Args:
        error: 異常物件
        context: 錯誤上下文
    """
    AgentErrorHandler.display_error(error, context=context)
