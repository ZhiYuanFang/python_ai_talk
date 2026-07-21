"""
意图分类节点

业务说明：
使用 LLM 对用户输入进行意图分类，识别事件类型、动作和关键词。
作为向量匹配失败后的降级方案，使用 LLM 的语义理解能力进行意图识别。

设计思路：
1. 构建包含事件字典的系统提示词
2. 调用 LLM 进行意图分类
3. 解析 LLM 返回的结构化 JSON 结果
4. 处理新事件场景：当事件不在可用列表中时，推断 event_type 和 event_unit
5. 优先使用向量匹配已提取的数量，LLM 提取作为 fallback
"""

import json
import logging
from typing import Any, Dict, Optional

from langchain_core.messages import SystemMessage, HumanMessage

from app.config.settings import settings
from app.feeding.graphs.nodes.prompts.intent_classification import (
    build_intent_classification_system_prompt,
    build_intent_classification_user_message,
)
from app.feeding.schemas.intent import IntentResponse
from app.feeding.utils.quantity_extractor import extract_quantity_from_text
from app.shared.llm_client import LLMClient

# 初始化日志记录器
logger = logging.getLogger(__name__)


def _match_feeding_event(
    event_name: str, event_dictionary: list[dict[str, Any]]
) -> Optional[dict[str, Any]]:
    """
    在事件字典中匹配事件

    业务逻辑：
    1. 遍历事件字典，查找名称完全匹配的事件
    2. 如果没有完全匹配，尝试查找名称包含关系
    3. 返回匹配到的事件信息

    Args:
        event_name: LLM 识别出的事件名称
        event_dictionary: 事件字典列表

    Returns:
        匹配到的事件字典，未匹配到时返回 None
    """
    # 首先尝试精确匹配
    for event in event_dictionary:
        if event["event_name"] == event_name:
            return event

    # 尝试包含匹配
    for event in event_dictionary:
        if event_name in event["event_name"] or event["event_name"] in event_name:
            return event

    return None


def _parse_intent_result(content: str) -> Dict[str, Any]:
    """
    解析 LLM 返回的意图结果

    业务逻辑：
    1. 清理 LLM 返回的内容（去除 markdown 代码块标记）
    2. 解析 JSON 格式的意图结果
    3. 处理解析错误，返回默认的 conversation 类型意图

    Args:
        content: LLM 返回的原始文本内容

    Returns:
        解析后的意图结果字典
    """
    try:
        # 清理 markdown 代码块标记
        cleaned = content.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        result = json.loads(cleaned)
        logger.info(f"LLM 意图解析成功: {json.dumps(result, ensure_ascii=False)}")
        return result
    except json.JSONDecodeError as e:
        logger.error(f"LLM 返回内容 JSON 解析失败: {e}, content={content[:200]}")
        # 返回默认的 conversation 类型
        return {
            "target_type": "conversation",
            "action": "reply",
            "event_name": "",
            "event_id": "",
            "keywords": [],
            "content": content,
        }


async def classify_intent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    意图分类节点

    业务逻辑：
    1. 从状态中获取用户输入和事件字典
    2. 构建系统提示词和用户消息
    3. 调用 LLM 进行意图分类
    4. 解析 LLM 返回的结构化 JSON 结果
    5. 处理新事件场景：当事件不在可用列表中时，使用 LLM 返回的 event_type 和 event_unit
    6. 优先使用向量匹配已提取的数量，未提取到时尝试本地提取作为 fallback
    7. 根据匹配情况设置 need_confirm 标志

    Args:
        state: 当前图状态，包含用户输入文本、事件字典等信息

    Returns:
        更新后的状态字典，包含意图分类结果
    """
    text = state.get("text", "")
    event_dictionary = state.get("event_dictionary", [])
    device_no = state.get("device_no", "")

    # 获取模型配置
    model_config = state.get("model", {"provider": "deepseek", "name": "deepseek-chat"})

    logger.info(
        f"开始意图分类: device_no={device_no}, "
        f"text={text[:20]}..., "
        f"model={model_config.get('provider')}/{model_config.get('name')}"
    )

    try:
        # 构建提示词
        system_prompt = build_intent_classification_system_prompt(event_dictionary)
        user_message = build_intent_classification_user_message(text, event_dictionary)

        # 创建 LLM 客户端
        llm_client = LLMClient(
            provider=model_config.get("provider", "deepseek"),
            model_name=model_config.get("name", "deepseek-chat"),
            temperature=0.0,
            max_tokens=4096,
        )

        # 调用 LLM
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]

        response = await llm_client.invoke(messages)

        # 解析意图结果
        intent_result = _parse_intent_result(response.content)

        # 处理新事件场景
        if intent_result.get("event_name") and not intent_result.get("event_id"):
            matched_event = _match_feeding_event(
                intent_result["event_name"], event_dictionary
            )
            if matched_event:
                # 匹配到已有事件，使用已有事件的 ID
                intent_result["event_id"] = matched_event["event_id"]
                intent_result["is_new_event"] = False
            else:
                # 未匹配到已有事件，标记为新事件
                intent_result["is_new_event"] = True
                # 确保 event_type 和 event_unit 有值
                if not intent_result.get("event_type"):
                    intent_result["event_type"] = "one"
                if not intent_result.get("event_unit"):
                    intent_result["event_unit"] = "次"
        elif intent_result.get("event_id"):
            # 匹配到已有事件
            intent_result["is_new_event"] = False

        # 数量提取：优先使用向量匹配已提取的数量，未提取到时尝试本地提取
        vector_quantity = None
        if state.get("intent_result") and state["intent_result"].get("quantity") is not None:
            vector_quantity = state["intent_result"]["quantity"]

        if vector_quantity is not None:
            intent_result["quantity"] = vector_quantity
            logger.info(f"使用向量匹配提取的数量: quantity={vector_quantity}")
        elif intent_result.get("quantity") is None:
            # 向量匹配未提取到数量，尝试本地提取
            extracted_quantity = extract_quantity_from_text(text)
            if extracted_quantity is not None:
                intent_result["quantity"] = extracted_quantity
                logger.info(f"本地提取数量成功: quantity={extracted_quantity}")

        # 确保所有字段都有默认值
        intent_result.setdefault("target_type", "conversation")
        intent_result.setdefault("action", "reply")
        intent_result.setdefault("event_name", "")
        intent_result.setdefault("event_id", "")
        intent_result.setdefault("quantity", None)
        intent_result.setdefault("event_type", None)
        intent_result.setdefault("event_unit", None)
        intent_result.setdefault("is_new_event", False)
        intent_result.setdefault("match_source", "llm")
        intent_result.setdefault("match_confidence", 1.0)
        intent_result.setdefault("keywords", [])
        intent_result.setdefault("content", "")

        # 多事件场景处理
        if intent_result.get("action") == "multi" and intent_result.get("events"):
            # 为多事件中的每个事件匹配 event_id
            for event in intent_result["events"]:
                if event.get("event_name") and not event.get("event_id"):
                    matched = _match_feeding_event(event["event_name"], event_dictionary)
                    if matched:
                        event["event_id"] = matched["event_id"]
                    else:
                        event["event_id"] = ""
                # 多事件中每个事件也尝试提取数量
                if event.get("quantity") is None:
                    event_quantity = extract_quantity_from_text(text)
                    if event_quantity is not None:
                        event["quantity"] = event_quantity

        logger.info(
            f"意图分类完成: target_type={intent_result['target_type']}, "
            f"action={intent_result['action']}, "
            f"event_name={intent_result['event_name']}, "
            f"event_id={intent_result['event_id']}, "
            f"quantity={intent_result.get('quantity')}, "
            f"event_type={intent_result.get('event_type')}, "
            f"event_unit={intent_result.get('event_unit')}, "
            f"is_new_event={intent_result.get('is_new_event')}"
        )

        return {
            "intent_result": intent_result,
            "match_confidence": 1.0,  # LLM 分类的置信度默认为 1.0
            "match_source": "llm",
        }

    except Exception as e:
        logger.error(f"意图分类失败: {e}", exc_info=True)
        # 分类失败时返回默认的 conversation 类型
        return {
            "intent_result": {
                "target_type": "conversation",
                "action": "reply",
                "event_name": "",
                "event_id": "",
                "quantity": None,
                "event_type": None,
                "event_unit": None,
                "is_new_event": False,
                "match_source": "llm",
                "match_confidence": 0.0,
                "keywords": [],
                "content": "AI 服务暂时不可用，请稍后再试",
            },
            "match_confidence": 0.0,
            "match_source": "llm",
        }
