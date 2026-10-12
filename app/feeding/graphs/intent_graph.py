"""
意图分析图定义

业务说明：
分句/单事件多维拼装 → 确认 END / 批量落库 / 模板查记录 / 预测播报。
已删除整包意图缓存免确认与满血一次多 events 分类主路径。
路由按六轨 target_type + read_source（R·predict 优先于 R·record）。
"""

import logging
from typing import Any

from langgraph.graph import StateGraph, START, END

from app.feeding.graphs.nodes.execute_history_crud import execute_history_crud
from app.feeding.graphs.nodes.resolve_segments import resolve_segments
from app.feeding.graphs.nodes.speak_history import speak_history
from app.feeding.graphs.nodes.speak_predict import speak_predict
from app.feeding.graphs.nodes.thinking_messages import get_thinking_message
from app.feeding.graphs.states.intent_state import IntentState
from app.feeding.schemas.intent_result import coerce_intent_result
from app.feeding.services.history_crud import infer_route_kind
from app.feeding.services.intent_events import normalize_intent_events
from app.shared.constants import IntentOp, TargetType, normalize_target_rail
from app.shared.graphs.node_thinking import with_node_thinking
from app.shared.graphs.state_patch import state_get

logger = logging.getLogger(__name__)

State = IntentState


def _route_after_segments(state: Any) -> str:
    """
    多维拼装后：需确认/重说/other/exit → END；
    read+predict → 预测播报；read+record → 查史；C/U/D → 落库。
    """
    if state_get(state, "need_confirm"):
        return "end"
    intent = coerce_intent_result(state_get(state, "intent_result")).to_plain_dict()
    intent = normalize_intent_events(intent)
    # 引导重说：已有 content，直接 END
    if intent.get("segment_failed"):
        return "end"
    # 缺量：不得直执行（双保险，与 need_confirm 门控一致）
    events = [e for e in (intent.get("events") or []) if isinstance(e, dict)]
    if intent.get("missing_quantity") or any(e.get("missing_quantity") for e in events):
        return "end"
    target_raw = str(intent.get("target_type") or TargetType.OTHER.value).lower()
    target = normalize_target_rail(target_raw)
    read_source = str(intent.get("read_source") or "").strip().lower()
    # 兼容旧顶层 predict/history
    if target_raw == TargetType.PREDICT.value:
        target, read_source = TargetType.READ.value, "predict"
    elif target_raw == TargetType.HISTORY.value:
        target, read_source = TargetType.READ.value, "record"
    if target in (TargetType.OTHER.value, TargetType.EXIT.value):
        return "end"
    # R·predict 不得进 speak_history
    if target == TargetType.READ.value and read_source == "predict":
        return "speak_predict"
    if target_raw == TargetType.PREDICT.value:
        return "speak_predict"
    kind = infer_route_kind(intent)
    if (
        target == TargetType.READ.value
        or kind == IntentOp.READ.value
        or target_raw == TargetType.HISTORY.value
    ):
        return "speak_history"
    if kind == "cud" or target in (
        TargetType.CREATE.value,
        TargetType.UPDATE.value,
        TargetType.DELETE.value,
    ):
        return "execute_history_crud"
    return "end"


def _wrap(name: str, fn):
    return with_node_thinking(name, fn, get_thinking_message)


def build_intent_graph():
    """构建意图分析图（段多维拼装，无整包缓存、无满血 classify）。"""
    graph = StateGraph(State)

    graph.add_node("resolve_segments", _wrap("resolve_segments", resolve_segments))
    graph.add_node(
        "execute_history_crud",
        _wrap("execute_history_crud", execute_history_crud),
    )
    graph.add_node("speak_history", _wrap("speak_history", speak_history))
    graph.add_node("speak_predict", _wrap("speak_predict", speak_predict))

    graph.add_edge(START, "resolve_segments")
    graph.add_conditional_edges(
        "resolve_segments",
        _route_after_segments,
        {
            "end": END,
            "speak_predict": "speak_predict",
            "speak_history": "speak_history",
            "execute_history_crud": "execute_history_crud",
        },
    )
    graph.add_edge("execute_history_crud", END)
    graph.add_edge("speak_history", END)
    graph.add_edge("speak_predict", END)

    logger.info("意图分析图构建完成（段多维 / 落库 / 查史 / 预测）")
    return graph.compile()


intent_graph = build_intent_graph()
