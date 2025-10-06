"""
Agent 快取管理系統

功能：
- 快取 Agent 執行結果，節省 API 成本
- 支援 TTL（過期時間）
- 透過 .env 控制開關（預設關閉）
- 開發階段可關閉快取進行測試

使用範例：
    from utils.cache_manager import AgentCache

    cache = AgentCache()
    key = cache.get_cache_key('CopywritingAgent', params)

    # 嘗試取得快取
    cached_result = cache.get(key)
    if cached_result:
        return cached_result

    # 執行 Agent
    result = await agent.run(...)

    # 儲存快取
    cache.set(key, result)
"""

import os
import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Optional, Dict
import streamlit as st


class AgentCache:
    """Agent 結果快取管理器"""

    def __init__(self, ttl_seconds: int = None):
        """
        初始化快取管理器

        Args:
            ttl_seconds: 快取過期時間（秒），None 則從 .env 讀取
        """
        # 從 .env 讀取快取設定
        self.enabled = os.getenv('ENABLE_AGENT_CACHE', 'false').lower() == 'true'
        self.ttl = ttl_seconds or int(os.getenv('AGENT_CACHE_TTL', '3600'))  # 預設 1 小時

        # 使用 session_state 儲存快取（Streamlit 生命週期內有效）
        if 'agent_cache_storage' not in st.session_state:
            st.session_state['agent_cache_storage'] = {}

        self.cache: Dict[str, tuple] = st.session_state['agent_cache_storage']

    def get_cache_key(self, agent_name: str, params: dict) -> str:
        """
        生成快取 key

        Args:
            agent_name: Agent 名稱
            params: 參數字典

        Returns:
            快取 key (MD5 hash)
        """
        # 排序參數確保一致性
        sorted_params = json.dumps(params, sort_keys=True, ensure_ascii=False)
        content = f"{agent_name}:{sorted_params}"

        # 生成 MD5 hash
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """
        取得快取

        Args:
            key: 快取 key

        Returns:
            快取的結果，若不存在或已過期則返回 None
        """
        # 快取未啟用
        if not self.enabled:
            return None

        # 檢查是否存在
        if key not in self.cache:
            return None

        result, timestamp = self.cache[key]

        # 檢查是否過期
        if datetime.now() - timestamp > timedelta(seconds=self.ttl):
            # 已過期，刪除
            del self.cache[key]
            return None

        return result

    def set(self, key: str, value: Any) -> None:
        """
        設定快取

        Args:
            key: 快取 key
            value: 要快取的值
        """
        # 快取未啟用
        if not self.enabled:
            return

        # 儲存結果與時間戳
        self.cache[key] = (value, datetime.now())

    def clear(self) -> None:
        """清空所有快取"""
        self.cache.clear()
        st.session_state['agent_cache_storage'] = {}

    def get_stats(self) -> Dict[str, Any]:
        """
        取得快取統計資料

        Returns:
            包含快取數量、過期數量等資訊的字典
        """
        total = len(self.cache)
        expired = 0

        for key, (_, timestamp) in self.cache.items():
            if datetime.now() - timestamp > timedelta(seconds=self.ttl):
                expired += 1

        return {
            'enabled': self.enabled,
            'total_entries': total,
            'expired_entries': expired,
            'active_entries': total - expired,
            'ttl_seconds': self.ttl
        }

    def cleanup_expired(self) -> int:
        """
        清理過期的快取項目

        Returns:
            清理的數量
        """
        if not self.enabled:
            return 0

        expired_keys = []
        for key, (_, timestamp) in self.cache.items():
            if datetime.now() - timestamp > timedelta(seconds=self.ttl):
                expired_keys.append(key)

        for key in expired_keys:
            del self.cache[key]

        return len(expired_keys)


def get_agent_cache() -> AgentCache:
    """
    取得全域 Agent 快取實例（單例模式）

    Returns:
        AgentCache 實例
    """
    if 'global_agent_cache' not in st.session_state:
        st.session_state['global_agent_cache'] = AgentCache()

    return st.session_state['global_agent_cache']


# 裝飾器：自動快取 Agent 執行結果
def cache_agent_result(agent_name: str = None):
    """
    裝飾器：自動快取 Agent 執行結果

    Args:
        agent_name: Agent 名稱，若不提供則使用類別名稱

    使用範例：
        @cache_agent_result()
        async def generate_copy(self, product_name, target_audience, ...):
            ...
    """
    def decorator(func):
        async def wrapper(self, *args, **kwargs):
            # 取得 Agent 名稱
            name = agent_name or self.__class__.__name__

            # 建立參數字典（用於快取 key）
            # 合併位置參數和關鍵字參數
            import inspect
            sig = inspect.signature(func)
            params = {}

            # 取得參數名稱
            param_names = list(sig.parameters.keys())[1:]  # 跳過 self

            # 位置參數
            for i, arg in enumerate(args):
                if i < len(param_names):
                    params[param_names[i]] = str(arg)[:100]  # 限制長度避免 key 過長

            # 關鍵字參數
            for k, v in kwargs.items():
                params[k] = str(v)[:100]

            # 取得快取管理器
            cache = get_agent_cache()

            # 生成快取 key
            cache_key = cache.get_cache_key(name, params)

            # 嘗試取得快取
            cached_result = cache.get(cache_key)

            if cached_result is not None:
                # 顯示快取命中訊息
                if cache.enabled:
                    st.info(f"✨ 使用快取結果（節省 API 成本）")
                return cached_result

            # 執行原始函數
            result = await func(self, *args, **kwargs)

            # 儲存快取
            cache.set(cache_key, result)

            return result

        return wrapper
    return decorator
