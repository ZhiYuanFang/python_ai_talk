"""
成长轨迹 LangGraph

业务说明：
弱史 + 画像 + 月龄 →（可选 confirm_prior）→ plan_next → ask/reconfirm/final → generate。
使用 MemorySaver + interrupt；节点经 with_node_thinking 推编排字幕。
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.care_alert.graphs.nodes.resolve_baby_age import resolve_baby_age
from app.growth_trajectory.graphs.nodes.ask_question import (
    ask_question,
    final_free_text,
    reconfirm,
)
from app.growth_trajectory.graphs.nodes.confirm_prior import confirm_prior
from app.growth_trajectory.graphs.nodes.generate_trajectory import generate_trajectory
from app.growth_trajectory.graphs.nodes.plan_next import plan_next
from app.growth_trajectory.graphs.nodes.thinking_messages import get_thinking_message
from app.growth_trajectory.graphs.states.growth_trajectory_state import (
    GrowthTrajectoryState,
)
from app.shared.graphs.node_thinking import with_node_thinking
from app.shared.graphs.nodes.fetch_baby_profile import fetch_baby_profile
from app.shared.graphs.nodes.fetch_history import fetch_history
from app.shared.graphs.state_patch import state_get

logger = logging.getLogger(__name__)

# 进程内 checkpointer：按 session_id(thread_id) 恢复 interrupt
_checkpointer = MemorySaver()


def _wrap(name: str, fn):
    """包装节点：先推 thinking 再执行。"""
    return with_node_thinking(name, fn, get_thinking_message)


def route_after_profile(state: Any) -> Literal["confirm_prior", "plan_next"]:
    """有 prior_feedback 且尚未确认 → confirm_prior；否则 plan_next。"""
    prior = state_get(state, "prior_feedback") or []
    confirmed = bool(state_get(state, "confirmed_prior"))
    if prior and not confirmed:
        return "confirm_prior"
    return "plan_next"


def route_after_plan(
    state: Any,
) -> Literal["ask_question", "reconfirm", "final_free_text", "generate"]:
    """按 plan_decision 分支；默认 ask。"""
    decision = str(state_get(state, "plan_decision") or "").strip().lower()
    if decision in ("generate", "enough", "done"):
        return "generate"
    if decision == "reconfirm":
        return "reconfirm"
    if decision == "final_ask":
        return "final_free_text"
    return "ask_question"


def build_growth_trajectory_graph():
    """构建并 compile 成长轨迹图（带 MemorySaver）。"""
    workflow = StateGraph(GrowthTrajectoryState)

    workflow.add_node("fetch_history", _wrap("fetch_history", fetch_history))
    workflow.add_node(
        "fetch_baby_profile", _wrap("fetch_baby_profile", fetch_baby_profile)
    )
    workflow.add_node("resolve_baby_age", _wrap("resolve_baby_age", resolve_baby_age))
    workflow.add_node("confirm_prior", _wrap("confirm_prior", confirm_prior))
    workflow.add_node("plan_next", _wrap("plan_next", plan_next))
    workflow.add_node("ask_question", _wrap("ask_question", ask_question))
    workflow.add_node("reconfirm", _wrap("reconfirm", reconfirm))
    workflow.add_node("final_free_text", _wrap("final_free_text", final_free_text))
    workflow.add_node("generate", _wrap("generate", generate_trajectory))

    workflow.add_edge(START, "fetch_history")
    workflow.add_edge("fetch_history", "fetch_baby_profile")
    workflow.add_edge("fetch_baby_profile", "resolve_baby_age")
    workflow.add_conditional_edges(
        "resolve_baby_age",
        route_after_profile,
        {
            "confirm_prior": "confirm_prior",
            "plan_next": "plan_next",
        },
    )
    # confirm 后必须 plan，禁止直 generate
    workflow.add_edge("confirm_prior", "plan_next")
    workflow.add_conditional_edges(
        "plan_next",
        route_after_plan,
        {
            "ask_question": "ask_question",
            "reconfirm": "reconfirm",
            "final_free_text": "final_free_text",
            "generate": "generate",
        },
    )
    workflow.add_edge("ask_question", "plan_next")
    workflow.add_edge("reconfirm", "plan_next")
    workflow.add_edge("final_free_text", "generate")
    workflow.add_edge("generate", END)

    graph = workflow.compile(checkpointer=_checkpointer)
    logger.info("成长轨迹状态图构建完成（MemorySaver + interrupt）")
    return graph


growth_trajectory_graph = build_growth_trajectory_graph()
