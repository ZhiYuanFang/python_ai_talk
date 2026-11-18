"""
护理留意模型解析

业务说明：
Go 可省略 model（字符串 deepseek|zhipu，或完整 ModelConfig）。
缺省返回空占位 dict，实际上游由 llm_client TEMPORARY runtime 决定。
zhipu 与 glm 等价，沿用 llm_client.normalize_llm_provider。
无 clinic 配额逻辑；不恢复保底换模链。
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Union

from app.feeding.schemas.intent import ModelConfig
from app.shared.llm_client import normalize_llm_provider

# 仅传提供商字符串时的默认模型名（与常见 Go clinic/deepseek 配置对齐）
_DEFAULT_MODEL_BY_PROVIDER = {
    "deepseek": "deepseek-chat",
    "glm": "glm-4.7-flash",
}


def resolve_model_config(
    model: Optional[Union[str, ModelConfig, Dict[str, Any]]],
) -> Dict[str, Any]:
    """
    将请求中的 model 规范为图/LLM 使用的 dict；缺省返回空占位。

    业务逻辑：
    1. None → {}（交由 llm_client TEMPORARY runtime）
    2. 字符串 → provider + 默认 name
    3. ModelConfig / dict → 取 provider/name/max_in_flight
    4. provider 经 normalize（zhipu→glm）

    Args:
        model: 请求字段（可省略）

    Returns:
        {"provider", "name", "max_in_flight"}；缺省为 {}

    Raises:
        ValueError: 传入但不完整/未知的 model
    """
    if model is None:
        return {}

    if isinstance(model, str):
        provider = normalize_llm_provider(model)
        name = _DEFAULT_MODEL_BY_PROVIDER.get(provider)
        if not name:
            raise ValueError(f"不支持的 model 字符串: {model!r}，请用 deepseek 或 zhipu")
        return {
            "provider": provider,
            "name": name,
            "max_in_flight": 3,
        }

    if isinstance(model, ModelConfig):
        provider = normalize_llm_provider(model.provider)
        name = (model.name or "").strip()
        if not name:
            name = _DEFAULT_MODEL_BY_PROVIDER.get(provider, "")
        if not name:
            raise ValueError("model.name 不能为空")
        return {
            "provider": provider,
            "name": name,
            "max_in_flight": int(model.max_in_flight or 3),
        }

    if isinstance(model, dict):
        raw_provider = model.get("provider") or model.get("Provider") or ""
        provider = normalize_llm_provider(str(raw_provider))
        name = str(model.get("name") or model.get("Name") or "").strip()
        if not name:
            name = _DEFAULT_MODEL_BY_PROVIDER.get(provider, "")
        if not provider or not name:
            raise ValueError("model 对象须含 provider 与 name（或可解析的默认名）")
        max_in_flight = model.get("max_in_flight", model.get("maxInFlight", 3))
        return {
            "provider": provider,
            "name": name,
            "max_in_flight": int(max_in_flight or 3),
        }

    raise ValueError(f"无法解析 model: {type(model)}")
