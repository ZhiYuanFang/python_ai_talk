"""
意图分析图定义

业务说明：
缓存 → 可选备注探针 → 分类 → 确认 END / 批量落库 / 模板查记录。
不再调用 clinic agent，feeding 不得导入 clinic。
"""

import logging

from langgraph.graph import StateGraph, START, END

from app.feeding.graphs.nodes.classify_intent import classify_intent
from app.feeding.graphs.nodes.execute_history_crud import execute_history_crud
from app.feeding.graphs.nodes.match_event_by_vector import match_event_by_vector
from app.feeding.graphs.nodes.match_intent_cache import match_intent_cache
from app.feeding.graphs.nodes.remark_probe import remark_probe
from app.feeding.graphs.nodes.speak_history import speak_history
from app.feeding.graphs.nodes.thinking_messages import get_thinking_message
from app.feeding.graphs.states.intent_state import IntentState
from app.feeding.services.history_crud import infer_op
from app.shared.constants import IntentOp, MatchSource, TargetType
from app.shared.graphs.node_thinking import with_node_thinking

logger = logging.getLogger(__name__)

State = IntentState


def route_after_cache(state: State) -> str:
    """缓存命中 CRUD 则执行或查记录；否则探针。"""
    if not state.get("intent_cache_hit"):
        return "remark_probe"
    op = infer_op(state.get("intent_result") or {})
    if op == IntentOp.READ.value:
        return "speak_history"
    if op in (IntentOp.CREATE.value, IntentOp.UPDATE.value, IntentOp.DELETE.value):
        return "execute_history_crud"
    return "end"


def route_after_vector_match(state: State) -> str:
    """向量仅作单一 create 快路径；否则分类。"""
    match_source = state.get("match_source", MatchSource.LLM.value)
    if match_source == MatchSource.LLM.value:
        return "classify_intent"
    if state.get("need_confirm"):
        return "end"
    return "execute_history_crud"


def route_after_classify(state: State) -> str:
    """分类后：确认则 END；read 模板；CUD 落库；其余 END。"""
    if state.get("need_confirm"):
        return "end"
    intent = state.get("intent_result") or {}
    op = infer_op(intent)
    target = intent.get("target_type", TargetType.CONVERSATION.value)
    if op == IntentOp.READ.value or target == TargetType.HISTORY.value:
        return "speak_history"
    if op in (IntentOp.CREATE.value, IntentOp.UPDATE.value, IntentOp.DELETE.value):
        return "execute_history_crud"
    return "end"


def _wrap(name: str, fn):
    return with_node_thinking(name, fn, get_thinking_message)


def build_intent_graph() -> StateGraph:
    """构建意图分析图（无 clinic）。"""
    graph = StateGraph(State)

    graph.add_node("match_intent_cache", _wrap("match_intent_cache", match_intent_cache))
    graph.add_node("remark_probe", _wrap("remark_probe", remark_probe))
    graph.add_node(
        "match_event_by_vector",
        _wrap("match_event_by_vector", match_event_by_vector),
    )
    graph.add_node("classify_intent", _wrap("classify_intent", classify_intent))
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
            "remark_probe": "remark_probe",
            "speak_history": "speak_history",
            "execute_history_crud": "execute_history_crud",
            "end": END,
        },
    )
    graph.add_edge("remark_probe", "match_event_by_vector")
    graph.add_conditional_edges(
        "match_event_by_vector",
        route_after_vector_match,
        {
            "classify_intent": "classify_intent",
            "execute_history_crud": "execute_history_crud",
            "end": END,
        },
    )
    graph.add_conditional_edges(
        "classify_intent",
        route_after_classify,
        {
            "end": END,
            "speak_history": "speak_history",
            "execute_history_crud": "execute_history_crud",
        },
    )
    graph.add_edge("execute_history_crud", END)
    graph.add_edge("speak_history", END)

    logger.info("意图分析图构建完成（缓存/探针/分类/落库/模板查记录）")
    return graph.compile()


intent_graph = build_intent_graph()

