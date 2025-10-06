"""
LLM 服務層
提供統一的 LLM 調用接口，支援快取、錯誤處理、成本監控與 API Key 輪替。
"""

from __future__ import annotations

import csv
import json
import hashlib
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

import streamlit as st
from dotenv import load_dotenv

from utils.api_keys import get_api_key_manager
from utils.logging_manager import log_event, log_exception, log_metric
from utils.security import sanitize_payload

# 嘗試導入 OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    st.warning("⚠️ OpenAI 套件未安裝，AI 功能將無法使用。請執行：pip install openai")

# 載入環境變數，確保 CLI 與 Streamlit 共用設定
load_dotenv()

LLM_USAGE_FILE = Path(os.getenv("LLM_USAGE_FILE", "data/history/llm_usage.csv"))
LLM_USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)


def _append_usage_log(payload: Dict[str, Any]) -> None:
    is_new = not LLM_USAGE_FILE.exists()
    with LLM_USAGE_FILE.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=payload.keys())
        if is_new:
            writer.writeheader()
        writer.writerow(payload)


class LLMService:
    """LLM 服務類別"""

    def __init__(self) -> None:
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.model_name = os.getenv("OPENAI_MODEL", "gpt-5-nano")
        try:
            self.cache_ttl = int(os.getenv("CACHE_TTL", "3600"))
        except ValueError:
            self.cache_ttl = 3600

        self.usage_stats = {
            'total_calls': 0,
            'cache_hits': 0,
            'total_tokens': 0,
            'estimated_cost': 0.0,
        }

        self.api_key_manager = get_api_key_manager()
        self.client: Optional[OpenAI] = None
        self.current_key: Optional[str] = None
        if OPENAI_AVAILABLE:
            self._initialize_client()

    # ------------------------------------------------------------------
    # 客戶端與 API Key
    # ------------------------------------------------------------------
    def _initialize_client(self) -> None:
        key = None
        if self.api_key_manager.has_keys():
            key = self.api_key_manager.acquire()
        else:
            single_key = os.getenv("OPENAI_API_KEY")
            if single_key:
                key = single_key

        if not key:
            st.warning("⚠️ 尚未設定 OPENAI_API_KEY，AI 功能將停用。")
            return

        try:
            self.client = OpenAI(api_key=key)
            self.current_key = key
            log_event("llm_client_initialized", {"key_suffix": key[-4:]})
        except Exception as exc:
            log_exception(exc, "initialize_openai_client")
            self.client = None

    def _rotate_key(self) -> None:
        if not self.api_key_manager.has_keys():
            return
        self._initialize_client()

    # ------------------------------------------------------------------
    # 快取
    # ------------------------------------------------------------------
    def _get_cache_key(self, prompt: str, model: str) -> str:
        return hashlib.md5(f"{model}:{prompt}".encode("utf-8")).hexdigest()

    def _get_cached_response(self, cache_key: str) -> Optional[str]:
        entry = self.cache.get(cache_key)
        if not entry:
            return None
        if datetime.now() - entry['timestamp'] > timedelta(seconds=self.cache_ttl):
            del self.cache[cache_key]
            return None
        self.usage_stats['cache_hits'] += 1
        return entry['response']

    def _set_cache(self, cache_key: str, response: str) -> None:
        self.cache[cache_key] = {
            'response': response,
            'timestamp': datetime.now(),
        }

    # ------------------------------------------------------------------
    # 核心呼叫
    # ------------------------------------------------------------------
    def is_available(self) -> bool:
        return OPENAI_AVAILABLE and self.client is not None

    def _log_usage(self, model: str, tokens: int, cost: float, source: str) -> None:
        payload = {
            'timestamp': datetime.utcnow().isoformat(),
            'model': model,
            'tokens': tokens,
            'cost': cost,
            'source': source,
        }
        _append_usage_log(payload)
        log_metric("llm_cost", cost, namespace="llm")

    def _estimate_cost(self, tokens: int, model_name: str) -> float:
        if 'gpt-4' in model_name:
            rate = 0.015
        elif 'gpt-5' in model_name:
            rate = 0.0004
        else:
            rate = 0.0005
        return tokens * rate / 1000

    def _handle_failure(self, error: Exception) -> str:
        lowered = str(error).lower()
        if "rate limit" in lowered:
            return "⚠️ API 調用次數已達上限，請稍後再試。"
        if "api key" in lowered or "authentication" in lowered:
            return "❌ API 金鑰無效或已過期，請檢查設定。"
        if "insufficient_quota" in lowered:
            return "⚠️ API 配額不足，請檢查 OpenAI 帳戶。"
        if "timeout" in lowered:
            return "⚠️ 請求逾時，請稍後再試。"
        return f"❌ AI 分析失敗：{error}"

    def generate_insights(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        use_cache: bool = True,
        source: str = "insights"
    ) -> str:
        if not self.is_available():
            return "❌ AI 功能目前無法使用，請設定 OPENAI_API_KEY"

        model_name = model or self.model_name
        cache_key = self._get_cache_key(prompt, model_name)
        if use_cache:
            cached = self._get_cached_response(cache_key)
            if cached:
                log_event("llm_cache_hit", {"model": model_name})
                return cached

        try:
            response = self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一位專業的 Meta 廣告投放顧問，擅長分析廣告數據並提供可執行的優化建議。",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            result = response.choices[0].message.content
            self.usage_stats['total_calls'] += 1

            tokens = getattr(getattr(response, 'usage', None), 'total_tokens', 0)
            self.usage_stats['total_tokens'] += tokens
            cost = self._estimate_cost(tokens, model_name)
            self.usage_stats['estimated_cost'] += cost
            self._log_usage(model_name, tokens, cost, source)

            if use_cache:
                self._set_cache(cache_key, result)

            if self.current_key:
                self.api_key_manager.report_success(self.current_key)

            log_event("llm_call_success", {
                "model": model_name,
                "tokens": tokens,
                "cost": cost,
            })
            return result

        except Exception as error:  # pylint: disable=broad-except
            log_exception(error, "llm_generate_insights")
            if self.current_key:
                self.api_key_manager.report_failure(self.current_key)
                self._rotate_key()
            return self._handle_failure(error)

    def generate_structured_output(
        self,
        prompt: str,
        schema: Dict[str, Any],
        model: Optional[str] = None,
        use_cache: bool = True,
        source: str = "structured"
    ) -> Dict[str, Any]:
        raw = self.generate_insights(
            prompt=f"請依照以下 JSON Schema 返回結果：\n{json.dumps(schema, ensure_ascii=False, indent=2)}\n\n{prompt}",
            model=model,
            use_cache=use_cache,
            source=source,
        )
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"error": "AI 回傳的格式無法解析", "raw": raw}


__all__ = ["LLMService"]
