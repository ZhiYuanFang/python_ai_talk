"""
是否需要喂养历史：门禁节点

业务说明：
LangGraph 节点：在 judge_data_requirement 之前，用 LLM 宽松判断是否需要喂养历史。
force_needs_history 时跳过 LLM，直接 needs_history=true。
失败默认 true；判定为 false 时同时清空 history_events，便于跳过拉取路径。

设计思路：
1. 读 user_input / question、model_config、force_needs_history
2. 强制或 LLM → needs_history
3. false 时附带 history_events=[]，供条件跳过路径使用
"""

import json
import logging
import re
from typing import Any, Dict

from app.shared.graphs.nodes.prompts.needs_history import (
    build_needs_history_system_prompt,
    build_needs_history_user_message,
)
from app.shared.llm_client import LLMModelConfig, llm_client

logger = logging.getLogger(__name__)


async def judge_needs_history(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    门禁节点：写出 needs_history；false 时置空 history_events。

    Args:
        state: 当前图状态

    Returns:
        需要更新的 State 字段
    """
    # 上游（intent history）已认定查记录：省 LLM，钉死 true
    if state.get("force_needs_history"):
        return {"needs_history": True}

    user_text = state.get("user_input") or state.get("question", "")
    model_config_dict = state.get("model_config", {}) or {}

    if not str(user_text).strip():
        # 无问题文本：保守拉取
        return {"needs_history": False}

    model_config = LLMModelConfig(**model_config_dict)
    system_prompt = build_needs_history_system_prompt()
    user_message = build_needs_history_user_message(str(user_text))

    try:
        response = await llm_client.invoke(
            messages=[{"role": "user", "content": user_message}],
            model_config=model_config,
            system_prompt=system_prompt,
        )
        needs = _parse_needs_history(response.content)
    except Exception as e:
        logger.error(f"喂养历史门禁 LLM 调用失败，默认需要历史: {e}")
        needs = False

    if needs:
        return {"needs_history": True}
    # 跳过后续拉取：先清空，避免残留旧 state
    return {"needs_history": False, "history_events": []}


def _parse_needs_history(content: str) -> bool:
    """
    解析门禁 JSON；无法解析时返回 True（fail-open）。

    Args:
        content: LLM 文本

    Returns:
        是否需要喂养历史
    """
    content = (content or "").strip()
    json_match = re.search(r"```json\s*([\s\S]*?)\s*```", content)
    json_str = json_match.group(1).strip() if json_match else content

    try:
        parsed = json.loads(json_str)
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        logger.warning(
            f"门禁结果 JSON 解析失败，默认 true: {e}, 原始内容: {content[:100]}"
        )
        return True

    if not isinstance(parsed, dict) or "needs_history" not in parsed:
        logger.warning("门禁结果缺少 needs_history，默认 true")
        return True

    value = parsed.get("needs_history")
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "1", "yes"):
            return True
        if lowered in ("false", "0", "no"):
            return False
    if isinstance(value, (int, float)):
        return bool(value)

    logger.warning(f"门禁 needs_history 类型异常: {value!r}，默认 true")
    return True
