"""
用户反馈处理节点

业务说明：
LangGraph 节点：处理用户对意图确认的反馈（确认/取消），执行数据飞轮和向量库维护。
用户确认后，根据匹配来源执行不同的飞轮逻辑；用户取消后，清理高置信度的错误匹配。

设计思路：
1. 从 State 中读取用户反馈、匹配来源、匹配置信度等信息
2. 确认反馈：根据匹配来源执行数据飞轮（LLM 匹配新增表达 / 向量匹配增加成功计数）
3. 取消反馈：对高置信度错误匹配执行向量删除，防止再次误匹配
4. 执行向量库质量检查和清理，保持数据健康

使用场景：
- 用户确认操作：触发数据飞轮，将用户表达或匹配成功信息反馈到向量库
- 用户取消操作：清理错误向量数据，防止重复误匹配，并引导用户重新描述
"""

import logging  # 导入日志模块
from typing import Any, Dict  # 导入类型提示

from app.feeding.services.event_vector_store import event_vector_store  # 导入事件向量存储实例

# 初始化日志记录器
logger = logging.getLogger(__name__)


async def handle_feedback(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    用户反馈处理节点函数

    业务逻辑：
    1. 从 State 中读取用户反馈、匹配来源、匹配置信度等关键信息
    2. 用户确认时：
       a. LLM 匹配来源：调用数据飞轮，将用户表达添加到向量库
       b. 向量匹配来源：递增成功计数，强化正确匹配
       c. 执行向量库质量检查和清理
       d. 多事件场景：将用户表达关联到第一个事件添加到向量库
    3. 用户取消时：
       a. 高置信度错误匹配：删除错误向量数据，防止再次误匹配
       b. 返回对话意图，引导用户重新描述需求

    Args:
        state: 当前图状态，包含 user_feedback、match_source、match_confidence 等字段

    Returns:
        需要更新的 State 字段字典，包含 should_update_vector、feedback_recorded 等字段

    Side Effects:
        - 确认时可能向向量库添加用户表达（数据飞轮）
        - 确认时可能递增向量记录的成功计数
        - 确认时可能触发向量库质量检查和清理
        - 取消时可能删除向量库中的错误匹配记录
    """
    # 从 State 中获取用户反馈，值为 "confirm" 或 "reject"
    user_feedback = state.get("user_feedback", "")

    # 从 State 中获取匹配来源，值为 "llm" 或 "vector"
    match_source = state.get("match_source", "")

    # 从 State 中获取匹配置信度，默认为 0.0
    match_confidence = state.get("match_confidence", 0.0)

    # 从 State 中获取用户输入文本
    user_input = state.get("user_input", "")

    # 从 State 中获取意图分类结果
    intent_result = state.get("intent_result", {})

    # 从 State 中获取匹配到的向量记录 ID
    matched_vector_id = state.get("matched_vector_id", "")

    # 从意图结果中提取动作类型
    action = intent_result.get("action", "")

    # 判断是否为多事件场景
    is_multi_event = (action == "multi")

    # 提取事件信息（多事件场景取第一个事件）
    if is_multi_event:
        events = intent_result.get("events", [])
        if events:
            first_event = events[0]
            event_name = first_event.get("event_name", "")
            event_id = first_event.get("event_id", "")
            event_action = first_event.get("action", "")
        else:
            event_name = ""
            event_id = ""
            event_action = ""
    else:
        # 单事件场景：从意图结果中提取事件名称和事件 ID
        event_name = intent_result.get("event_name", "")
        event_id = intent_result.get("event_id", "")
        event_action = action

    # 判断用户反馈类型：确认或取消
    if user_feedback == "confirm":
        # 用户确认操作

        # 根据匹配来源执行不同的数据飞轮逻辑
        if match_source == "llm":
            # LLM 匹配来源：数据飞轮！将用户表达添加到向量库
            # 业务说明：LLM 匹配成功后，用户表达是有价值的训练样本
            # 多事件场景：将完整用户表达关联到第一个事件添加到向量库
            event_vector_store.add_user_expression(
                event_id=event_id,  # 关联的事件 ID（多事件取第一个）
                event_name=event_name,  # 关联的事件名称（多事件取第一个）
                expression=user_input,  # 用户的自然语言表达（完整表达）
                action=event_action,  # 动作类型（多事件取第一个事件的动作）
            )
            # 记录数据飞轮动作日志
            logger.info(f"数据飞轮：LLM 匹配确认，添加用户表达: event_id={event_id}, expression={user_input[:30]}...")

        # 检查是否为向量匹配且存在匹配的向量 ID
        if match_source == "vector" and matched_vector_id:
            # 向量匹配来源：递增成功计数，强化正确匹配
            event_vector_store.increment_success_count(matched_vector_id)
            # 记录成功计数递增日志
            logger.info(f"向量匹配确认，递增成功计数: vector_id={matched_vector_id}")

        # 执行向量库质量检查和清理，保持数据健康
        event_vector_store.check_and_cleanup()

        # 返回确认结果，标记需要更新向量库
        return {"should_update_vector": True, "feedback_recorded": True}

    else:
        # 用户取消操作

        # 检查是否为高置信度错误匹配，需要清理错误向量
        # 业务说明：高置信度（>=0.90）却匹配错误，说明该向量数据有误，应删除防止再次误匹配
        if match_confidence >= 0.90 and matched_vector_id:
            # 删除错误的向量数据
            event_vector_store.delete_vector(matched_vector_id)
            # 记录删除错误向量日志
            logger.info(f"用户取消高置信度匹配，删除错误向量: vector_id={matched_vector_id}, confidence={match_confidence}")

        # 返回取消结果，同时返回对话意图引导用户重新描述
        return {
            "should_update_vector": False,  # 不需要更新向量库
            "feedback_recorded": True,  # 反馈已记录
            "intent_result": {
                "target_type": "conversation",  # 切换为对话场景
                "action": "reply",  # 动作为回复
                "event_name": "",  # 清空事件名称
                "event_id": "",  # 清空事件 ID
                "events": [],  # 清空事件列表（多事件场景）
                "keywords": [],  # 清空关键词
                "content": "抱歉，我理解错了，请您重新描述。",  # 引导用户重新描述的提示文案
            },
        }
