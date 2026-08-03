"""
诊疗状态图

业务说明：
数据准备：隐式飞轮 → needs_history 门禁 →（可选）范围判断 →（可选）fetch_history
→（可选）search_vectors → fetch_baby_profile。
纯查记录（skip_knowledge=True）时跳过知识向量检索。
force_needs_history 时门禁钉死需要历史。
节点经 with_node_thinking 在业务前推送 custom thinking。

流式回答在路由层调用 stream_response；本图只负责上下文准备。
"""

import logging

from langgraph.graph import StateGraph, END

from app.clinic.graphs.nodes.implicit_feedback import implicit_feedback
from app.clinic.graphs.nodes.thinking_messages import get_thinking_message
from app.clinic.graphs.states.clinic_state import ClinicState
from app.shared.graphs.history_gate import should_fetch_history
from app.shared.graphs.node_thinking import with_node_thinking
from app.shared.graphs.nodes.judge_needs_history import judge_needs_history
from app.shared.graphs.nodes.judge_data_requirement import judge_data_requirement
from app.shared.graphs.nodes.fetch_history import fetch_history
from app.shared.graphs.nodes.search_vectors import search_vectors
from app.shared.graphs.nodes.fetch_baby_profile import fetch_baby_profile

logger = logging.getLogger(__name__)


def _route_after_needs_history(state: ClinicState) -> str:
    """门禁之后：需要历史则进范围判断，否则跳到向量或画像。"""
    if should_fetch_history(state):
        return "judge_data_requirement"
    if state.get("skip_knowledge"):
        return "fetch_baby_profile"
    return "search_vectors"


def _route_after_fetch_history(state: ClinicState) -> str:
    """fetch_history 之后：跳过知识检索或继续 search_vectors。"""
    if state.get("skip_knowledge"):
        return "fetch_baby_profile"
    return "search_vectors"


def _wrap(name: str, fn):
    """挂 clinic thinking 文案。"""
    return with_node_thinking(name, fn, get_thinking_message)


def build_clinic_graph() -> StateGraph:
    """
    构建诊疗状态图（含飞轮、needs_history / skip_knowledge 条件边）。
    """
    workflow = StateGraph(ClinicState)

    workflow.add_node("implicit_feedback", _wrap("implicit_feedback", implicit_feedback))
    workflow.add_node(
        "judge_needs_history", _wrap("judge_needs_history", judge_needs_history)
    )
    workflow.add_node(
        "judge_data_requirement",
        _wrap("judge_data_requirement", judge_data_requirement),
    )
    workflow.add_node("fetch_history", _wrap("fetch_history", fetch_history))
    workflow.add_node("search_vectors", _wrap("search_vectors", search_vectors))
    workflow.add_node(
        "fetch_baby_profile", _wrap("fetch_baby_profile", fetch_baby_profile)
    )

    workflow.set_entry_point("implicit_feedback")
    workflow.add_edge("implicit_feedback", "judge_needs_history")

    workflow.add_conditional_edges(
        "judge_needs_history",
        _route_after_needs_history,
        {
            "judge_data_requirement": "judge_data_requirement",
            "search_vectors": "search_vectors",
            "fetch_baby_profile": "fetch_baby_profile",
        },
    )
    workflow.add_edge("judge_data_requirement", "fetch_history")
    workflow.add_conditional_edges(
        "fetch_history",
        _route_after_fetch_history,
        {
            "search_vectors": "search_vectors",
            "fetch_baby_profile": "fetch_baby_profile",
        },
    )
    workflow.add_edge("search_vectors", "fetch_baby_profile")
    workflow.add_edge("fetch_baby_profile", END)

    graph = workflow.compile()
    logger.info("诊疗状态图构建完成（飞轮+needs_history/skip_knowledge+thinking）")
    return graph


clinic_graph = build_clinic_graph()
