"""
诊疗状态图

业务说明：
数据准备：judge → fetch_history →（可选）search_vectors → fetch_baby_profile。
纯查记录（skip_knowledge=True）时跳过知识向量检索。

流式回答在路由层调用 stream_response；本图只负责上下文准备。
"""

import logging

from langgraph.graph import StateGraph, END

from app.clinic.graphs.states.clinic_state import ClinicState
from app.shared.graphs.nodes.judge_data_requirement import judge_data_requirement
from app.shared.graphs.nodes.fetch_history import fetch_history
from app.shared.graphs.nodes.search_vectors import search_vectors
from app.shared.graphs.nodes.fetch_baby_profile import fetch_baby_profile

logger = logging.getLogger(__name__)


def _route_after_fetch_history(state: ClinicState) -> str:
    """fetch_history 之后：跳过知识检索或继续 search_vectors。"""
    if state.get("skip_knowledge"):
        return "fetch_baby_profile"
    return "search_vectors"


def build_clinic_graph() -> StateGraph:
    """
    构建诊疗状态图（含 skip_knowledge 条件边）。
    """
    workflow = StateGraph(ClinicState)

    workflow.add_node("judge_data_requirement", judge_data_requirement)
    workflow.add_node("fetch_history", fetch_history)
    workflow.add_node("search_vectors", search_vectors)
    workflow.add_node("fetch_baby_profile", fetch_baby_profile)

    workflow.set_entry_point("judge_data_requirement")

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
    logger.info("诊疗状态图构建完成（支持 skip_knowledge）")
    return graph


clinic_graph = build_clinic_graph()
