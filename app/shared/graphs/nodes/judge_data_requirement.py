"""
数据需求判断节点

业务说明：
LangGraph 节点：调用 LLM 根据用户问题判断需要查询哪些类型的历史记录以及时间范围。
输出 event_ids（事件ID列表，而非事件名称，因为ID是稳定标识）和 time_range。
包含 fallback 策略：LLM 返回异常时使用默认配置。

设计思路：
1. 从 State 中读取用户问题（user_input 或 question）、事件字典、模型配置
2. 调用 LLM 判断数据需求
3. 解析 JSON，验证 event_ids 的合法性（在事件字典中存在）
4. LLM 失败时使用 fallback：event_ids 为空（全部）、time_range=last_7_days
5. 返回 data_requirement 更新 State
"""

import json
import logging
from typing import Any, Dict, List, Optional

from app.shared.graphs.nodes.prompts.data_requirement import (
    build_data_requirement_system_prompt,
    build_data_requirement_user_message,
)
from app.shared.graphs.state_patch import state_get
from app.shared.llm_client import llm_client, llm_model_config_from_mapping
from app.shared.llm_json import loads_llm_json
from app.shared.schemas.data_requirement import DataRequirement

# 初始化日志记录器
logger = logging.getLogger(__name__)

# 支持的时间范围值
VALID_TIME_RANGES = {
    "today",
    "yesterday",
    "last_2_days",
    "last_7_days",
    "last_30_days",
    "custom",
}

# 默认数据需求配置（fallback 使用）
DEFAULT_DATA_REQUIREMENT = {
    "event_ids": [],
    "time_range": "last_7_days",
    "limit": 20,
}


async def judge_data_requirement(state: Any) -> Dict[str, Any]:
    """
    数据需求判断节点：产出 DataRequirement 写入 State。
    """
    user_text = state_get(state, "user_input") or state_get(state, "question", "") or ""
    event_dictionary = state_get(state, "event_dictionary", []) or []
    if not event_dictionary:
        logger.warning("事件字典为空，使用默认数据需求")
        return {"data_requirement": DataRequirement.model_validate(DEFAULT_DATA_REQUIREMENT)}

    model_config = llm_model_config_from_mapping(
        state_get(state, "llm_model") or state_get(state, "model_config")
    )

    system_prompt = build_data_requirement_system_prompt()
    user_message = build_data_requirement_user_message(user_text, event_dictionary)

    try:
        response = await llm_client.invoke(
            messages=[{"role": "user", "content": user_message}],
            model_config=model_config,
            system_prompt=system_prompt,
        )

        requirement = _parse_data_requirement(response.content)

        valid_event_ids = _extract_valid_event_ids(event_dictionary)
        requirement["event_ids"] = [
            eid for eid in requirement.get("event_ids", [])
            if eid in valid_event_ids
        ]

        if requirement.get("time_range") not in VALID_TIME_RANGES:
            requirement["time_range"] = DEFAULT_DATA_REQUIREMENT["time_range"]

        limit = requirement.get("limit", DEFAULT_DATA_REQUIREMENT["limit"])
        if not isinstance(limit, int) or limit <= 0:
            limit = DEFAULT_DATA_REQUIREMENT["limit"]
        if limit > 500:
            limit = 500
        requirement["limit"] = limit

        from app.shared.history_window import enum_to_unix

        start_u, end_u = enum_to_unix(str(requirement.get("time_range") or "last_7_days"))
        requirement["start_time"] = start_u
        requirement["end_time"] = end_u

    except Exception as e:
        logger.error(f"数据需求判断 LLM 调用失败: {str(e)}")
        requirement = DEFAULT_DATA_REQUIREMENT.copy()
        from app.shared.history_window import enum_to_unix

        start_u, end_u = enum_to_unix(str(requirement.get("time_range") or "last_7_days"))
        requirement["start_time"] = start_u
        requirement["end_time"] = end_u

    return {"data_requirement": DataRequirement.model_validate(requirement)}


def _parse_data_requirement(content: str) -> Dict[str, Any]:
    """
    解析 LLM 返回的数据需求结果

    业务逻辑：
    尝试从 LLM 返回内容中提取 JSON 格式的数据需求信息。
    兼容被 ```json ``` 包裹或直接输出 JSON 的情况。

    Args:
        content: LLM 返回的文本内容

    Returns:
        解析后的数据需求字典
    """
    result = DEFAULT_DATA_REQUIREMENT.copy()
    content = (content or "").strip()
    try:
        parsed = loads_llm_json(content)
        if not isinstance(parsed, dict):
            raise ValueError("数据需求 JSON 须为对象")

        # 提取 event_ids（统一为字符串，兼容 LLM 返回 number）
        event_ids = parsed.get("event_ids", [])
        if isinstance(event_ids, list):
            result["event_ids"] = [
                sid for eid in event_ids if (sid := _to_event_id_str(eid)) is not None
            ]

        # 提取 time_range
        if "time_range" in parsed:
            result["time_range"] = parsed["time_range"]

        # 提取 limit
        if "limit" in parsed and _is_valid_int(parsed["limit"]):
            result["limit"] = int(parsed["limit"])

    except (json.JSONDecodeError, ValueError, TypeError) as e:
        logger.warning(f"数据需求结果 JSON 解析失败: {str(e)}, 原始内容: {content[:100]}")

    return result


def _extract_valid_event_ids(event_dictionary: list) -> List[str]:
    """
    从事件字典中提取所有有效的事件ID

    业务逻辑：
    将事件字典中的 event_id 提取为字符串列表，用于验证 LLM 返回的 event_ids。
    比较在字符串空间进行，避免 int/str 漂移导致 membership 静默失败。

    Args:
        event_dictionary: 事件字典列表

    Returns:
        有效的事件ID字符串列表
    """
    valid_ids = []
    for event in event_dictionary:
        eid = event.get("event_id", event.get("id"))
        sid = _to_event_id_str(eid)
        if sid is not None:
            valid_ids.append(sid)
    return valid_ids


def _to_event_id_str(value: Any) -> Optional[str]:
    """
    将候选事件ID规范为正整数字符串；无效则返回 None。

    兼容 LLM 返回的 number 或 digit 字符串（如 52 / \"52\" → \"52\"）。
    """
    if value is None or value == "":
        return None
    try:
        int_val = int(value)
        if int_val <= 0:
            return None
        return str(int_val)
    except (ValueError, TypeError):
        return None


def _is_valid_int(value: Any) -> bool:
    """
    判断值是否可以转换为有效正整数

    Args:
        value: 待判断的值

    Returns:
        是否为有效正整数
    """
    try:
        int_val = int(value)
        return int_val > 0
    except (ValueError, TypeError):
        return False
