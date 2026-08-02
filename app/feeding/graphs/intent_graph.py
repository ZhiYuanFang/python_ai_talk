"""
意图分析图定义

业务说明：
使用 LangGraph 定义意图分析的状态图，协调向量匹配、意图分类与 clinic agent。
history / conversation / suggest 均走 call_clinic_agent（查记录由 clinic 拉历史答题）。

确认/消歧改为同一 /intent + conversation_id 的 pending 自由文本续聊。

设计思路：
1. 向量匹配 → 按置信度路由（查询句已在 match 内降级 LLM）
2. LLM 分类后：feeding END；history/conversation/suggest → clinic agent；exit END
"""

import logging
from typing import Any, Dict

from langgraph.graph import StateGraph, START, END

from app.feeding.graphs.nodes.call_clinic_agent import call_clinic_agent
from app.feeding.graphs.nodes.classify_intent import classify_intent
from app.feeding.graphs.nodes.match_event_by_vector import match_event_by_vector
from app.feeding.graphs.states.intent_state import IntentState
from app.shared.constants import MatchSource, TargetType

logger = logging.getLogger(__name__)

State = IntentState


def route_after_vector_match(state: State) -> str:
    """
    向量匹配后的路由决策（供图边与 intent 流式步进共用）。

    - match_source 为 llm：降级至 LLM 分类
    - 否则 END（含高置信直接结果、中置信 need_confirm，由路由层 pending 处理）
    """
    match_source = state.get("match_source", MatchSource.LLM.value)
    need_confirm = state.get("need_confirm", False)

    logger.info(
        f"向量匹配后路由决策: match_source={match_source}, "
        f"need_confirm={need_confirm}"
    )

    if match_source == MatchSource.LLM.value:
        return "classify_intent"
    return "end"


def route_after_classify(state: State) -> str:
    """
    意图分类后的路由决策（供图边与 intent 流式步进共用）。

    - feeding（含 multi）：END，由路由层做叶子校验/消歧/软确认
    - history / conversation / suggest：clinic agent
    - exit / 其他：直接结束
    """
    intent_result = state.get("intent_result") or {}
    target_type = intent_result.get("target_type", TargetType.CONVERSATION.value)

    logger.info(f"意图分类后路由决策: target_type={target_type}")

    if target_type == TargetType.FEEDING.value:
        return "end"
    if target_type in (
        TargetType.HISTORY.value,
        TargetType.CONVERSATION.value,
        TargetType.SUGGEST.value,
    ):
        return "call_clinic_agent"
    return "end"


_route_after_vector_match = route_after_vector_match
_route_after_classify = route_after_classify


def build_intent_graph() -> StateGraph:
    """构建意图分析图（history 并入 clinic agent）。"""
    graph = StateGraph(State)

    graph.add_node("match_event_by_vector", match_event_by_vector)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("call_clinic_agent", call_clinic_agent)

    graph.add_edge(START, "match_event_by_vector")

    graph.add_conditional_edges(
        "match_event_by_vector",
        route_after_vector_match,
        {
            "classify_intent": "classify_intent",
            "end": END,
        },
    )

    graph.add_conditional_edges(
        "classify_intent",
        route_after_classify,
        {
            "end": END,
            "call_clinic_agent": "call_clinic_agent",
        },
    )

    graph.add_edge("call_clinic_agent", END)

    logger.info("意图分析图构建完成（history→clinic agent；pending 由路由处理）")
    return graph.compile()


intent_graph = build_intent_graph()
