"""
诊疗状态图

业务说明：
入口拉取宝宝画像与月龄，再经 needs_history 门禁按需拉喂养史；
不再挂隐式飞轮、Q&A 捷径或通识向量检索。流式/同步回答由路由层完成。
"""

import logging

from langgraph.graph import StateGraph, END

from app.clinic.graphs.nodes.thinking_messages import get_thinking_message
from app.clinic.graphs.states.clinic_state import ClinicState
from app.shared.graphs.history_gate import should_fetch_history
from app.shared.graphs.node_thinking import with_node_thinking
from app.shared.graphs.nodes.derive_baby_age import derive_baby_age
from app.shared.graphs.nodes.fetch_baby_profile import fetch_baby_profile
from app.shared.graphs.nodes.fetch_history import fetch_history
from app.shared.graphs.nodes.judge_data_requirement import judge_data_requirement
from app.shared.graphs.nodes.judge_needs_history import judge_needs_history

logger = logging.getLogger(__name__)


def _route_after_needs_history(state: ClinicState) -> str:
    """门禁之后：需要历史则进范围判断，否则直接结束准备阶段。"""
    if should_fetch_history(state):
        return "judge_data_requirement"
    return "end"


def _wrap(name: str, fn):
    """挂 clinic thinking 文案。"""
    return with_node_thinking(name, fn, get_thinking_message)


def build_clinic_graph() -> StateGraph:
    """构建诊疗状态图（画像/月龄 + needs_history，无通识/Q&A/隐式飞轮）。"""
    workflow = StateGraph(ClinicState)

    workflow.add_node(
        "fetch_baby_profile", _wrap("fetch_baby_profile", fetch_baby_profile)
    )
    workflow.add_node("derive_baby_age", _wrap("derive_baby_age", derive_baby_age))
    workflow.add_node(
        "judge_needs_history", _wrap("judge_needs_history", judge_needs_history)
    )
    workflow.add_node(
        "judge_data_requirement",
        _wrap("judge_data_requirement", judge_data_requirement),
    )
    workflow.add_node("fetch_history", _wrap("fetch_history", fetch_history))

    # 入口：原 implicit_feedback 之后的下一跳
    workflow.set_entry_point("fetch_baby_profile")
    workflow.add_edge("fetch_baby_profile", "derive_baby_age")
    workflow.add_edge("derive_baby_age", "judge_needs_history")
    workflow.add_conditional_edges(
        "judge_needs_history",
        _route_after_needs_history,
        {
            "judge_data_requirement": "judge_data_requirement",
            "end": END,
        },
    )
    workflow.add_edge("judge_data_requirement", "fetch_history")
    workflow.add_edge("fetch_history", END)

    graph = workflow.compile()
    logger.info("诊疗状态图构建完成（画像/月龄 + needs_history，无通识检索）")
    return graph


clinic_graph = build_clinic_graph()
