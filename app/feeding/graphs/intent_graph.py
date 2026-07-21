"""
意图分析图定义

业务说明：
使用 LangGraph 定义意图分析的状态图，协调向量匹配、意图分类、用户确认等节点。

设计思路：
1. 定义图的状态结构（State）
2. 添加向量匹配节点（match_event_by_vector）
3. 添加意图分类节点（classify_intent）
4. 添加用户确认节点（prepare_confirm）
5. 添加确认处理节点（handle_confirm_feedback）
6. 根据向量匹配结果进行条件路由
"""

import logging
from typing import Any, Dict

from langgraph.graph import StateGraph, START, END

from app.config.settings import settings
from app.feeding.graphs.nodes.classify_intent import classify_intent
from app.feeding.graphs.nodes.match_event_by_vector import match_event_by_vector

# 初始化日志记录器
logger = logging.getLogger(__name__)

# 定义图的状态类型
State = Dict[str, Any]


def _route_after_vector_match(state: State) -> str:
    """
    向量匹配后的路由决策

    业务逻辑：
    1. 从状态中读取向量匹配结果和置信度
    2. 根据 match_source 和 need_confirm 决定路由：
       - match_source 为 "llm" 时，降级至 LLM 分类
       - need_confirm 为 True 时，路由到用户确认节点
       - 否则直接结束（高置信度向量匹配）

    Args:
        state: 当前图状态

    Returns:
        下一个节点的名称（"classify_intent"、"prepare_confirm" 或 "end"）
    """
    # 从状态顶层读取 match_source（向量匹配节点返回在 state 顶层）
    match_source = state.get("match_source", "llm")
    need_confirm = state.get("need_confirm", False)

    logger.info(
        f"向量匹配后路由决策: match_source={match_source}, "
        f"need_confirm={need_confirm}"
    )

    if match_source == "llm":
        return "classify_intent"
    elif need_confirm is True:
        return "prepare_confirm"
    else:
        return "end"


def _route_after_confirm(state: State) -> str:
    """
    用户确认后的路由决策

    业务逻辑：
    1. 检查用户反馈状态
    2. 根据反馈决定是继续执行还是结束

    Args:
        state: 当前图状态

    Returns:
        下一个节点的名称（"classify_intent" 或 "end"）
    """
    user_feedback = state.get("user_feedback", "")

    logger.info(f"用户确认后路由决策: user_feedback={user_feedback}")

    if user_feedback == "confirm":
        return "end"
    else:
        # 用户拒绝，降级至 LLM 分类
        return "classify_intent"


async def prepare_confirm(state: State) -> State:
    """
    准备用户确认

    业务逻辑：
    1. 从状态中读取确认消息
    2. 设置确认状态，准备中断图执行等待用户反馈
    3. 返回包含确认消息的状态

    Args:
        state: 当前图状态

    Returns:
        更新后的状态，包含确认消息和确认状态
    """
    confirm_message = state.get("confirm_message", "请确认此操作")

    logger.info(f"准备用户确认: message={confirm_message}")

    return {
        **state,
        "need_confirm": True,
        "confirm_message": confirm_message,
    }


async def handle_confirm_feedback(state: State) -> State:
    """
    处理用户确认反馈

    业务逻辑：
    1. 从状态中读取用户反馈
    2. 根据反馈更新确认状态
    3. 返回更新后的状态

    Args:
        state: 当前图状态

    Returns:
        更新后的状态，包含用户反馈处理结果
    """
    user_feedback = state.get("user_feedback", "")

    logger.info(f"处理用户确认反馈: user_feedback={user_feedback}")

    return {
        **state,
        "need_confirm": False,
    }


def build_intent_graph() -> StateGraph:
    """
    构建意图分析图

    业务逻辑：
    1. 创建 StateGraph 实例
    2. 添加所有节点
    3. 添加边和条件路由
    4. 编译图

    Returns:
        编译后的 StateGraph 实例
    """
    # 创建图
    graph = StateGraph(State)

    # 添加节点
    graph.add_node("match_event_by_vector", match_event_by_vector)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("prepare_confirm", prepare_confirm)
    graph.add_node("handle_confirm_feedback", handle_confirm_feedback)

    # 添加边
    graph.add_edge(START, "match_event_by_vector")

    # 向量匹配后的条件路由
    graph.add_conditional_edges(
        "match_event_by_vector",
        _route_after_vector_match,
        {
            "classify_intent": "classify_intent",
            "prepare_confirm": "prepare_confirm",
            "end": END,
        },
    )

    # 确认准备后的条件路由
    graph.add_conditional_edges(
        "prepare_confirm",
        _route_after_confirm,
        {
            "classify_intent": "classify_intent",
            "end": END,
        },
    )

    # 确认处理后的路由
    graph.add_edge("handle_confirm_feedback", END)

    # 意图分类后直接结束
    graph.add_edge("classify_intent", END)

    logger.info("意图分析图构建完成")

    return graph.compile()
