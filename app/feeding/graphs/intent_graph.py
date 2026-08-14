"""
意图分析图定义

业务说明：
缓存 → 进行中探针 → 分类 →（有未定名称才）备注反查 → 确认 END / 批量落库 / 模板查记录。
分类后条件边门控反查；反查节点只做 Go 备注定事件。
分类前不再做备注 OOV 探针。不再做事件名向量匹配，不再调用 clinic agent。
"""

import logging
from typing import Any

from langgraph.graph import StateGraph, START, END

from app.feeding.graphs.nodes.classify_intent import classify_intent
from app.feeding.graphs.nodes.execute_history_crud import execute_history_crud
from app.feeding.graphs.nodes.match_intent_cache import match_intent_cache
from app.feeding.graphs.nodes.remark_probe import in_progress_probe
from app.feeding.graphs.nodes.resolve_remark_event import (
    has_unresolved_event_slots,
    resolve_remark_event,
)
from app.feeding.graphs.nodes.speak_history import speak_history
from app.feeding.graphs.nodes.thinking_messages import get_thinking_message
from app.feeding.graphs.states.intent_state import IntentState
from app.feeding.schemas.intent_result import coerce_intent_result
from app.feeding.services.history_crud import infer_op
from app.shared.constants import IntentOp, TargetType
from app.shared.graphs.node_thinking import with_node_thinking
from app.shared.graphs.state_patch import state_get

logger = logging.getLogger(__name__)

State = IntentState


def route_after_cache(state: Any) -> str:
    """缓存命中 CRUD 则执行或查记录；否则进行中探针。"""
    if not state_get(state, "intent_cache_hit"):
        return "in_progress_probe"
    intent = coerce_intent_result(state_get(state, "intent_result"))
    op = infer_op(intent.to_plain_dict())
    if op == IntentOp.READ.value:
        return "speak_history"
    if op in (IntentOp.CREATE.value, IntentOp.UPDATE.value, IntentOp.DELETE.value):
        return "execute_history_crud"
    return "end"


def _route_after_intent_ready(state: Any) -> str:
    """
    意图已就绪（无需再备注反查）后的落点。

    确认 → END；read/history → 模板播报；CUD → 批量落库；其余 END。
    """
    if state_get(state, "need_confirm"):
        return "end"
    intent = coerce_intent_result(state_get(state, "intent_result"))
    op = infer_op(intent.to_plain_dict())
    target = intent.target_type or TargetType.CONVERSATION.value
    if op == IntentOp.READ.value or target == TargetType.HISTORY.value:
        return "speak_history"
    if op in (IntentOp.CREATE.value, IntentOp.UPDATE.value, IntentOp.DELETE.value):
        return "execute_history_crud"
    return "end"


def route_after_classify(state: Any) -> str:
    """
    分类后：有「有名无 id」槽位才进备注反查；否则直达确认/执行/查记录。
    """
    intent = coerce_intent_result(state_get(state, "intent_result")).to_plain_dict()
    if has_unresolved_event_slots(intent):
        return "resolve_remark_event"
    return _route_after_intent_ready(state)


def route_after_remark_resolve(state: Any) -> str:
    """备注反查后：与分类后无未定名称时相同的确认/执行/查记录分支。"""
    return _route_after_intent_ready(state)


def _wrap(name: str, fn):
    return with_node_thinking(name, fn, get_thinking_message)


def build_intent_graph() -> StateGraph:
    """构建意图分析图（无事件名向量、无 clinic）。"""
    graph = StateGraph(State)

    graph.add_node("match_intent_cache", _wrap("match_intent_cache", match_intent_cache))
    graph.add_node("in_progress_probe", _wrap("in_progress_probe", in_progress_probe))
    graph.add_node("classify_intent", _wrap("classify_intent", classify_intent))
    graph.add_node(
        "resolve_remark_event", _wrap("resolve_remark_event", resolve_remark_event)
    )
    graph.add_node(
        "execute_history_crud",
        _wrap("execute_history_crud", execute_history_crud),
    )
    graph.add_node("speak_history", _wrap("speak_history", speak_history))

    graph.add_edge(START, "match_intent_cache")
    graph.add_conditional_edges(
        "match_intent_cache",
        route_after_cache,
        {
            "in_progress_probe": "in_progress_probe",
            "speak_history": "speak_history",
            "execute_history_crud": "execute_history_crud",
            "end": END,
        },
    )
    # 缓存未命中：进行中摘要 → 分类 →（条件）备注反查或直达落点
    graph.add_edge("in_progress_probe", "classify_intent")
    graph.add_conditional_edges(
        "classify_intent",
        route_after_classify,
        {
            "resolve_remark_event": "resolve_remark_event",
            "end": END,
            "speak_history": "speak_history",
            "execute_history_crud": "execute_history_crud",
        },
    )
    graph.add_conditional_edges(
        "resolve_remark_event",
        route_after_remark_resolve,
        {
            "end": END,
            "speak_history": "speak_history",
            "execute_history_crud": "execute_history_crud",
        },
    )
    graph.add_edge("execute_history_crud", END)
    graph.add_edge("speak_history", END)

    logger.info(
        "意图分析图构建完成（缓存/进行中/分类/条件备注反查/落库/模板查记录）"
    )
    return graph.compile()


intent_graph = build_intent_graph()
