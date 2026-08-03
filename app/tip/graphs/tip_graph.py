"""
小贴士状态图

业务说明：
使用 LangGraph StateGraph 构建小贴士数据准备流程。
入口为 fetch_history（路由预置 data_requirement，强制需要历史，不跑 judge / needs_history）。
节点经 with_node_thinking 在业务前推送 custom thinking。

流式回答在路由层调用 stream_tip_response。
"""

import logging

from langgraph.graph import StateGraph, END

from app.clinic.graphs.nodes.thinking_messages import get_thinking_message
from app.tip.graphs.states.tip_state import TipState
from app.shared.graphs.node_thinking import with_node_thinking
from app.shared.graphs.nodes.fetch_history import fetch_history
from app.shared.graphs.nodes.search_vectors import search_vectors
from app.shared.graphs.nodes.fetch_baby_profile import fetch_baby_profile
from app.tip.graphs.nodes.derive_baby_age import derive_baby_age

logger = logging.getLogger(__name__)


def _wrap(name: str, fn):
    return with_node_thinking(name, fn, get_thinking_message)


def build_tip_graph() -> StateGraph:
    """
    构建小贴士状态图：history → vectors → profile → derive_baby_age。
    """
    workflow = StateGraph(TipState)

    workflow.add_node("fetch_history", _wrap("fetch_history", fetch_history))
    workflow.add_node("search_vectors", _wrap("search_vectors", search_vectors))
    workflow.add_node(
        "fetch_baby_profile", _wrap("fetch_baby_profile", fetch_baby_profile)
    )
    workflow.add_node("derive_baby_age", _wrap("derive_baby_age", derive_baby_age))

    workflow.set_entry_point("fetch_history")
    workflow.add_edge("fetch_history", "search_vectors")
    workflow.add_edge("search_vectors", "fetch_baby_profile")
    workflow.add_edge("fetch_baby_profile", "derive_baby_age")
    workflow.add_edge("derive_baby_age", END)

    graph = workflow.compile()
    logger.info("小贴士状态图构建完成（入口 fetch_history + thinking）")
    return graph


tip_graph = build_tip_graph()
