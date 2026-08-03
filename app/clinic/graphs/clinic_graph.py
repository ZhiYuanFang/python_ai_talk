"""
诊疗状态图

业务说明：
隐式飞轮 → 画像/月龄 →（可选）改写+Q&A 捷径；命中则 END。
未命中 → needs_history 门禁 →（可选）范围/历史 →（可选）通识检索。
画像已在捷径前拉取，prepare 尾部不再重复 fetch_baby_profile。
"""

import logging

from langgraph.graph import StateGraph, END

from app.clinic.graphs.nodes.format_qa_answer import format_qa_answer
from app.clinic.graphs.nodes.implicit_feedback import implicit_feedback
from app.clinic.graphs.nodes.rewrite_standalone_question import (
    rewrite_standalone_question_node,
)
from app.clinic.graphs.nodes.search_qa_fast_path import search_qa_fast_path
from app.clinic.graphs.nodes.thinking_messages import get_thinking_message
from app.clinic.graphs.states.clinic_state import ClinicState
from app.config.settings import settings
from app.shared.graphs.history_gate import should_fetch_history
from app.shared.graphs.node_thinking import with_node_thinking
from app.shared.graphs.nodes.derive_baby_age import derive_baby_age
from app.shared.graphs.nodes.fetch_baby_profile import fetch_baby_profile
from app.shared.graphs.nodes.fetch_history import fetch_history
from app.shared.graphs.nodes.judge_data_requirement import judge_data_requirement
from app.shared.graphs.nodes.judge_needs_history import judge_needs_history
from app.shared.graphs.nodes.search_vectors import search_vectors
from app.shared.qa_fast_path import is_block_fast_path

logger = logging.getLogger(__name__)


def _route_after_derive_age(state: ClinicState) -> str:
    """月龄后：开捷径则改写；否则直接进 prepare。"""
    blocked, reason = is_block_fast_path(state)
    if blocked:
        logger.info("跳过 Q&A 捷径链: reason=%s", reason)
        return "judge_needs_history"
    if not bool(settings.qa_fast_path_enabled):
        return "judge_needs_history"
    return "rewrite_standalone_question"


def _route_after_qa_search(state: ClinicState) -> str:
    """Q&A 检索后：命中格式化，未命中进 prepare。"""
    if state.get("qa_hit"):
        return "format_qa_answer"
    logger.info(
        "Q&A miss 进入 prepare: reason=%s",
        state.get("qa_miss_reason") or state.get("qa_rewrite_miss_reason"),
    )
    return "judge_needs_history"


def _route_after_needs_history(state: ClinicState) -> str:
    """门禁之后：需要历史则进范围判断，否则向量或结束。"""
    if should_fetch_history(state):
        return "judge_data_requirement"
    if state.get("skip_knowledge"):
        return "end"
    return "search_vectors"


def _route_after_fetch_history(state: ClinicState) -> str:
    """fetch_history 之后。"""
    if state.get("skip_knowledge"):
        return "end"
    return "search_vectors"


def _wrap(name: str, fn):
    """挂 clinic thinking 文案。"""
    return with_node_thinking(name, fn, get_thinking_message)


def build_clinic_graph() -> StateGraph:
    """构建诊疗状态图（飞轮 + Q&A 捷径 + needs_history / skip_knowledge）。"""
    workflow = StateGraph(ClinicState)

    workflow.add_node("implicit_feedback", _wrap("implicit_feedback", implicit_feedback))
    workflow.add_node(
        "fetch_baby_profile", _wrap("fetch_baby_profile", fetch_baby_profile)
    )
    workflow.add_node("derive_baby_age", _wrap("derive_baby_age", derive_baby_age))
    workflow.add_node(
        "rewrite_standalone_question",
        _wrap("rewrite_standalone_question", rewrite_standalone_question_node),
    )
    workflow.add_node(
        "search_qa_fast_path", _wrap("search_qa_fast_path", search_qa_fast_path)
    )
    workflow.add_node("format_qa_answer", _wrap("format_qa_answer", format_qa_answer))
    workflow.add_node(
        "judge_needs_history", _wrap("judge_needs_history", judge_needs_history)
    )
    workflow.add_node(
        "judge_data_requirement",
        _wrap("judge_data_requirement", judge_data_requirement),
    )
    workflow.add_node("fetch_history", _wrap("fetch_history", fetch_history))
    workflow.add_node("search_vectors", _wrap("search_vectors", search_vectors))

    workflow.set_entry_point("implicit_feedback")
    workflow.add_edge("implicit_feedback", "fetch_baby_profile")
    workflow.add_edge("fetch_baby_profile", "derive_baby_age")
    workflow.add_conditional_edges(
        "derive_baby_age",
        _route_after_derive_age,
        {
            "rewrite_standalone_question": "rewrite_standalone_question",
            "judge_needs_history": "judge_needs_history",
        },
    )
    workflow.add_edge("rewrite_standalone_question", "search_qa_fast_path")
    workflow.add_conditional_edges(
        "search_qa_fast_path",
        _route_after_qa_search,
        {
            "format_qa_answer": "format_qa_answer",
            "judge_needs_history": "judge_needs_history",
        },
    )
    workflow.add_edge("format_qa_answer", END)

    workflow.add_conditional_edges(
        "judge_needs_history",
        _route_after_needs_history,
        {
            "judge_data_requirement": "judge_data_requirement",
            "search_vectors": "search_vectors",
            "end": END,
        },
    )
    workflow.add_edge("judge_data_requirement", "fetch_history")
    workflow.add_conditional_edges(
        "fetch_history",
        _route_after_fetch_history,
        {
            "search_vectors": "search_vectors",
            "end": END,
        },
    )
    workflow.add_edge("search_vectors", END)

    graph = workflow.compile()
    logger.info("诊疗状态图构建完成（飞轮+Q&A捷径+needs_history/skip_knowledge）")
    return graph


clinic_graph = build_clinic_graph()
