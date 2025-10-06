"""智能模型選擇工具。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict

from utils.logging_manager import log_event


@dataclass
class ModelProfile:
    name: str
    latency_ms: int
    cost_ratio: float
    max_tokens: int


DEFAULT_PROFILES: Dict[str, ModelProfile] = {
    "fast": ModelProfile("gpt-5-nano", latency_ms=1200, cost_ratio=1.0, max_tokens=4096),
    "balanced": ModelProfile("gpt-5-nano-instruct", latency_ms=1800, cost_ratio=1.2, max_tokens=8192),
    "quality": ModelProfile("gpt-4.1-mini", latency_ms=3200, cost_ratio=4.0, max_tokens=8192),
}


class ModelSelector:
    """根據任務複雜度與成本門檻挑選模型。"""

    def __init__(self) -> None:
        self.profiles = DEFAULT_PROFILES
        self.default_model = os.getenv("OPENAI_MODEL", "gpt-5-nano")

    def choose(self, complexity: str = "fast", prefer_quality: bool = False) -> str:
        complexity = complexity.lower()
        if prefer_quality and "quality" in self.profiles:
            model = self.profiles["quality"].name
        else:
            model = self.profiles.get(complexity, ModelProfile(self.default_model, 0, 0, 0)).name

        log_event("model_selected", {"complexity": complexity, "model": model, "prefer_quality": prefer_quality})
        return model


__all__ = ["ModelSelector"]
