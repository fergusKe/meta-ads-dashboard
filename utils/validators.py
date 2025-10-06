"""輸入驗證工具。"""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, ValidationError


class AgentInputModel(BaseModel):
    product_name: str | None = None
    target_audience: str | None = None
    budget: float | None = None
    objective: str | None = None


def validate_inputs(data: Dict[str, Any]) -> List[str]:
    """驗證使用者輸入，返回警告列表。"""
    warnings: List[str] = []
    try:
        AgentInputModel(**data)
    except ValidationError as exc:
        for err in exc.errors():
            warnings.append(f"欄位 {err['loc'][0]}：{err['msg']}")
    return warnings


__all__ = ["validate_inputs"]
