"""
意图分类节点

业务说明：
LangGraph 节点：调用 LLM 对用户输入进行意图分类。
解析 LLM 返回的 JSON 结果，填充 intent_result。
包含喂养场景事件名匹配和对话场景兜底文案逻辑。

设计思路：
1. 从 State 中读取 user_input、event_dictionary、model_config
2. 调用 LLM 进行意图分类
3. 解析 JSON 结果，提取 target_type、action、event_name、keywords、content
4. 喂养场景做事件名匹配，对话场景做兜底文案
5. 返回 intent_result 更新 State
"""

import json
import logging
import re
from typing import Any, Dict

from app.graphs.nodes.prompts.intent_classification import (
    build_intent_classification_system_prompt,
    build_intent_classification_user_message,
)
from app.services.llm_client import LLMModelConfig, llm_client

# 初始化日志记录器
logger = logging.getLogger(__name__)

# 对话场景兜底文案
# 业务说明：当 LLM 返回 conversation 意图但 content 为空时，使用预设兜底文案
CONVERSATION_FALLBACK = "抱歉，我暂时无法理解您的意思。您可以尝试描述具体的喂养记录查询或宝宝健康问题。"


async def classify_intent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    意图分类节点函数

    业务逻辑：
    1. 从 State 中读取用户输入、事件字典、模型配置
    2. 构建系统提示词和用户消息
    3. 调用 LLM 进行意图分类
    4. 解析 JSON 结果，提取意图信息
    5. 喂养场景：匹配事件名和事件ID
    6. 对话场景：填充兜底文案
    7. 返回 intent_result 更新 State

    Args:
        state: 当前图状态

    Returns:
        需要更新的 State 字段字典
    """
    # 读取输入参数
    user_input = state.get("user_input", "")
    event_dictionary = state.get("event_dictionary", [])
    model_config_dict = state.get("model_config", {})

    # 构建模型配置对象
    model_config = LLMModelConfig(**model_config_dict)

    # 构建提示词
    system_prompt = build_intent_classification_system_prompt(event_dictionary)
    user_message = build_intent_classification_user_message(user_input, event_dictionary)

    try:
        # 调用 LLM
        response = await llm_client.invoke(
            messages=[{"role": "user", "content": user_message}],
            model_config=model_config,
            system_prompt=system_prompt,
        )

        # 解析 LLM 返回的 JSON 结果
        intent_result = _parse_intent_result(response.content)

    except Exception as e:
        # LLM 调用失败，使用兜底
        logger.error(f"意图分类 LLM 调用失败: {str(e)}")
        intent_result = {
            "target_type": "conversation",
            "action": "reply",
            "event_name": "",
            "event_id": "",
            "keywords": [],
            "content": CONVERSATION_FALLBACK,
        }

    # 喂养场景：如果 event_name 为空，尝试从关键词匹配
    if intent_result.get("target_type") == "feeding":
        intent_result = _match_feeding_event(intent_result, user_input, event_dictionary)

    # 对话场景：如果 content 为空，使用兜底文案
    if intent_result.get("target_type") == "conversation" and not intent_result.get("content"):
        intent_result["content"] = CONVERSATION_FALLBACK

    # 返回更新后的 intent_result
    return {"intent_result": intent_result}


def _parse_intent_result(content: str) -> Dict[str, Any]:
    """
    解析 LLM 返回的意图分类结果

    业务逻辑：
    尝试从 LLM 返回内容中提取 JSON 格式的意图信息。
    兼容被 ```json ``` 包裹或直接输出 JSON 的情况。

    Args:
        content: LLM 返回的文本内容

    Returns:
        解析后的意图结果字典
    """
    # 默认结果
    default_result = {
        "target_type": "conversation",
        "action": "reply",
        "event_name": "",
        "event_id": "",
        "keywords": [],
        "content": "",
    }

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
        result = json.loads(json_str)
        # 确保必要字段存在
        for key in default_result:
            if key not in result:
                result[key] = default_result[key]
        return result
    except json.JSONDecodeError:
        logger.warning(f"意图分类结果 JSON 解析失败: {content[:100]}")
        return default_result


def _match_feeding_event(
    intent_result: Dict[str, Any],
    user_input: str,
    event_dictionary: list,
) -> Dict[str, Any]:
    """
    喂养场景事件名匹配

    业务逻辑：
    当 LLM 返回 feeding 意图但 event_name 为空时，
    尝试用用户文本中的关键词匹配事件字典，填充 event_name 和 event_id。

    Args:
        intent_result: 当前意图结果
        user_input: 用户输入文本
        event_dictionary: 事件字典列表

    Returns:
        匹配后的意图结果
    """
    if intent_result.get("event_name"):
        # 已有事件名，直接返回
        return intent_result

    # 遍历事件字典，尝试用关键词匹配
    for event in event_dictionary:
        event_name = event.get("event_name", "")
        keywords = event.get("keywords", [])
        event_id = event.get("event_id", event.get("id", ""))

        # 检查事件名是否出现在用户输入中
        if event_name and event_name in user_input:
            intent_result["event_name"] = event_name
            intent_result["event_id"] = str(event_id) if event_id else ""
            break

        # 检查关键词是否出现在用户输入中
        matched = False
        for kw in keywords:
            if kw and kw in user_input:
                matched = True
                break

        if matched:
            intent_result["event_name"] = event_name
            intent_result["event_id"] = str(event_id) if event_id else ""
            break

    return intent_result
