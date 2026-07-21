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
import re
from typing import Any, Dict, List

from app.clinic.graphs.nodes.prompts.data_requirement import (
    build_data_requirement_system_prompt,
    build_data_requirement_user_message,
)
from app.shared.llm_client import LLMModelConfig, llm_client

# 初始化日志记录器
logger = logging.getLogger(__name__)

# 支持的时间范围值
VALID_TIME_RANGES = {
    "today",
    "yesterday",
    "last_7_days",
    "last_30_days",
    "custom",
}

# 默认数据需求配置（fallback 使用）
DEFAULT_DATA_REQUIREMENT = {
    "event_ids": [],        # 空列表表示所有事件类型
    "time_range": "last_7_days",
    "limit": 20,
}


async def judge_data_requirement(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    数据需求判断节点函数

    业务逻辑：
    1. 从 State 中读取用户问题和事件字典
    2. 调用 LLM 判断需要哪些事件类型的历史记录和时间范围
    3. 解析结果，验证 event_ids 合法性（事件ID必须在事件字典中存在）
    4. 验证 time_range 合法性
    5. LLM 失败或结果异常时使用默认配置
    6. 返回 data_requirement 更新 State

    Args:
        state: 当前图状态

    Returns:
        需要更新的 State 字段字典
    """
    # 读取输入参数：优先用 user_input（intent_graph），其次用 question（clinic_graph）
    user_text = state.get("user_input") or state.get("question", "")
    event_dictionary = state.get("event_dictionary", [])
    model_config_dict = state.get("model_config", {})

    # 如果没有事件字典，使用默认配置（全部事件）
    if not event_dictionary:
        logger.warning("事件字典为空，使用默认数据需求")
        return {"data_requirement": DEFAULT_DATA_REQUIREMENT.copy()}

    # 构建模型配置对象
    model_config = LLMModelConfig(**model_config_dict)

    # 构建提示词
    system_prompt = build_data_requirement_system_prompt()
    user_message = build_data_requirement_user_message(user_text, event_dictionary)

    try:
        # 调用 LLM
        response = await llm_client.invoke(
            messages=[{"role": "user", "content": user_message}],
            model_config=model_config,
            system_prompt=system_prompt,
        )

        # 解析 LLM 返回的 JSON 结果
        requirement = _parse_data_requirement(response.content)

        # 验证 event_ids：只保留在事件字典中存在的 ID
        valid_event_ids = _extract_valid_event_ids(event_dictionary)
        requirement["event_ids"] = [
            eid for eid in requirement.get("event_ids", [])
            if eid in valid_event_ids
        ]

        # 验证 time_range
        if requirement.get("time_range") not in VALID_TIME_RANGES:
            requirement["time_range"] = DEFAULT_DATA_REQUIREMENT["time_range"]

        # 验证 limit
        limit = requirement.get("limit", DEFAULT_DATA_REQUIREMENT["limit"])
        if not isinstance(limit, int) or limit <= 0:
            limit = DEFAULT_DATA_REQUIREMENT["limit"]
        if limit > 500:
            limit = 500
        requirement["limit"] = limit

    except Exception as e:
        # LLM 调用失败，使用默认配置
        logger.error(f"数据需求判断 LLM 调用失败: {str(e)}")
        requirement = DEFAULT_DATA_REQUIREMENT.copy()

    return {"data_requirement": requirement}


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

    # 去除首尾空白
    content = content.strip()

    # 尝试提取 JSON 代码块
    json_match = re.search(r"```json\s*([\s\S]*?)\s*```", content)
    if json_match:
        json_str = json_match.group(1).strip()
    else:
        # 尝试直接解析 JSON
        json_str = content

    try:
        parsed = json.loads(json_str)

        # 提取 event_ids
        event_ids = parsed.get("event_ids", [])
        if isinstance(event_ids, list):
            result["event_ids"] = [int(eid) for eid in event_ids if _is_valid_int(eid)]

        # 提取 time_range
        if "time_range" in parsed:
            result["time_range"] = parsed["time_range"]

        # 提取 limit
        if "limit" in parsed and _is_valid_int(parsed["limit"]):
            result["limit"] = int(parsed["limit"])

    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"数据需求结果 JSON 解析失败: {str(e)}, 原始内容: {content[:100]}")

    return result


def _extract_valid_event_ids(event_dictionary: list) -> List[int]:
    """
    从事件字典中提取所有有效的事件ID

    业务逻辑：
    将事件字典中的 event_id 提取为整数列表，用于验证 LLM 返回的 event_ids。

    Args:
        event_dictionary: 事件字典列表

    Returns:
        有效的事件ID列表
    """
    valid_ids = []
    for event in event_dictionary:
        eid = event.get("event_id", event.get("id"))
        if eid is not None and _is_valid_int(eid):
            valid_ids.append(int(eid))
    return valid_ids


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
