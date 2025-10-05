"""
LLM 服務層
提供統一的 LLM 調用接口，支援快取、錯誤處理和成本控制
"""

import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import streamlit as st

# 嘗試導入 OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    st.warning("⚠️ OpenAI 套件未安裝，AI 功能將無法使用。請執行：pip install openai")


class LLMService:
    """LLM 服務類別"""

    def __init__(self):
        """初始化 LLM 服務"""
        self.client = None
        self.cache = {}
        self.cache_ttl = 3600  # 快取 1 小時

        # 成本監控
        self.usage_stats = {
            'total_calls': 0,
            'cache_hits': 0,
            'total_tokens': 0,
            'estimated_cost': 0.0
        }

        if OPENAI_AVAILABLE:
            self._initialize_client()

    def _initialize_client(self):
        """初始化 OpenAI 客戶端"""
        try:
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                self.client = OpenAI(api_key=api_key)
            else:
                # 嘗試從 Streamlit secrets 讀取
                if hasattr(st, 'secrets') and 'OPENAI_API_KEY' in st.secrets:
                    self.client = OpenAI(api_key=st.secrets['OPENAI_API_KEY'])
        except Exception as e:
            st.warning(f"⚠️ OpenAI 初始化失敗：{str(e)}")
            self.client = None

    def is_available(self) -> bool:
        """檢查 LLM 服務是否可用"""
        return OPENAI_AVAILABLE and self.client is not None

    def _get_cache_key(self, prompt: str) -> str:
        """生成快取鍵值"""
        return hashlib.md5(prompt.encode()).hexdigest()

    def _get_cached_response(self, cache_key: str) -> Optional[str]:
        """取得快取回應"""
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            # 檢查是否過期
            if datetime.now() - cached_data['timestamp'] < timedelta(seconds=self.cache_ttl):
                self.usage_stats['cache_hits'] += 1
                return cached_data['response']
            else:
                # 移除過期快取
                del self.cache[cache_key]
        return None

    def _set_cache(self, cache_key: str, response: str):
        """設定快取"""
        self.cache[cache_key] = {
            'response': response,
            'timestamp': datetime.now()
        }

    def generate_insights(
        self,
        prompt: str,
        model: str = "gpt-3.5-turbo",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        use_cache: bool = True
    ) -> str:
        """
        生成 AI 洞察

        Args:
            prompt: 提示詞
            model: 模型名稱 (gpt-3.5-turbo 或 gpt-4)
            max_tokens: 最大 token 數
            temperature: 溫度參數 (0-1，越高越隨機)
            use_cache: 是否使用快取

        Returns:
            AI 生成的回應文字
        """
        if not self.is_available():
            return "❌ AI 功能目前無法使用，請設定 OPENAI_API_KEY"

        # 檢查快取
        if use_cache:
            cache_key = self._get_cache_key(f"{model}:{prompt}")
            cached_response = self._get_cached_response(cache_key)
            if cached_response:
                return cached_response

        try:
            # 調用 OpenAI API
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一位專業的 Meta 廣告投放顧問，擅長分析廣告數據並提供可執行的優化建議。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )

            result = response.choices[0].message.content

            # 更新使用統計
            self.usage_stats['total_calls'] += 1
            if hasattr(response, 'usage'):
                tokens = response.usage.total_tokens
                self.usage_stats['total_tokens'] += tokens
                # 估算成本 (gpt-4o-mini: $0.15/1M input tokens, $0.60/1M output tokens)
                # 簡化計算：假設 input/output 各佔一半
                if 'gpt-4o-mini' in model or 'gpt-3.5' in model:
                    cost = (tokens / 1000000) * 0.375  # 平均成本
                elif 'gpt-4' in model:
                    cost = (tokens / 1000000) * 15  # GPT-4 平均成本
                else:
                    cost = (tokens / 1000000) * 0.375
                self.usage_stats['estimated_cost'] += cost

            # 存入快取
            if use_cache:
                self._set_cache(cache_key, result)

            return result

        except Exception as e:
            error_msg = str(e)

            # 根據錯誤類型返回不同訊息
            if "rate_limit" in error_msg.lower():
                return "⚠️ API 調用次數已達上限，請稍後再試。"
            elif "api_key" in error_msg.lower():
                return "❌ API 金鑰無效，請檢查 OPENAI_API_KEY 設定。"
            elif "insufficient_quota" in error_msg.lower():
                return "⚠️ API 配額不足，請檢查您的 OpenAI 帳戶。"
            else:
                return f"❌ AI 分析失敗：{error_msg}"

    def generate_structured_output(
        self,
        prompt: str,
        schema: Dict[str, Any],
        model: str = "gpt-3.5-turbo",
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        生成結構化 JSON 輸出

        Args:
            prompt: 提示詞
            schema: JSON Schema
            model: 模型名稱
            use_cache: 是否使用快取

        Returns:
            結構化的 JSON 物件
        """
        if not self.is_available():
            return {"error": "AI 功能目前無法使用"}

        # 在提示詞中要求 JSON 格式
        json_prompt = f"""
{prompt}

請以 JSON 格式回傳，遵循以下結構：
{json.dumps(schema, ensure_ascii=False, indent=2)}

只回傳 JSON，不要有其他文字。
"""

        try:
            response = self.generate_insights(
                json_prompt,
                model=model,
                temperature=0.5,  # 降低溫度以提高結構化輸出的可靠性
                use_cache=use_cache
            )

            # 嘗試解析 JSON
            # 移除可能的 markdown 標記
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            return json.loads(response)

        except json.JSONDecodeError:
            return {
                "error": "無法解析 AI 回應為 JSON 格式",
                "raw_response": response
            }
        except Exception as e:
            return {
                "error": f"生成結構化輸出失敗：{str(e)}"
            }

    def clear_cache(self):
        """清除所有快取"""
        self.cache = {}

    def get_usage_stats(self) -> Dict[str, Any]:
        """
        獲取使用統計

        Returns:
            包含使用統計的字典
        """
        cache_hit_rate = 0
        if self.usage_stats['total_calls'] > 0:
            cache_hit_rate = (self.usage_stats['cache_hits'] /
                            (self.usage_stats['total_calls'] + self.usage_stats['cache_hits'])) * 100

        return {
            **self.usage_stats,
            'cache_hit_rate': f"{cache_hit_rate:.1f}%",
            'cache_size': len(self.cache)
        }

    def reset_usage_stats(self):
        """重置使用統計"""
        self.usage_stats = {
            'total_calls': 0,
            'cache_hits': 0,
            'total_tokens': 0,
            'estimated_cost': 0.0
        }


# 全域 LLM 服務實例
_llm_service = None

def get_llm_service() -> LLMService:
    """取得全域 LLM 服務實例"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
