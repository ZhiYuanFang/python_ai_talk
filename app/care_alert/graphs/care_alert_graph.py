"""
护理留意分析状态图

业务说明：
复用 tip 同源数据准备节点：fetch_history → fetch_baby_profile，
再 resolve_baby_age → generate_care_alerts。
节点经 with_node_thinking 推编排字幕，供 SSE custom 消费。
不调用 search_vectors / 通识库。
"""

import logging

from langgraph.graph import END, StateGraph

from app.care_alert.graphs.nodes.generate_care_alerts import generate_care_alerts
from app.care_alert.graphs.nodes.resolve_baby_age import resolve_baby_age
from app.care_alert.graphs.nodes.thinking_messages import get_thinking_message
from app.care_alert.graphs.states.care_alert_state import CareAlertState
from app.shared.graphs.node_thinking import with_node_thinking
from app.shared.graphs.nodes.fetch_baby_profile import fetch_baby_profile
from app.shared.graphs.nodes.fetch_history import fetch_history

logger = logging.getLogger(__name__)


def _wrap(name: str, fn):
    """包装节点：先推 thinking 再执行。"""
    return with_node_thinking(name, fn, get_thinking_message)


def build_care_alert_graph() -> StateGraph:
    """
    构建护理留意图：历史 → 画像 → 月龄 → LLM 列表（无知识检索）。

    Returns:
        已 compile 的 LangGraph
    """
    workflow = StateGraph(CareAlertState)

    workflow.add_node("fetch_history", _wrap("fetch_history", fetch_history))
    workflow.add_node(
        "fetch_baby_profile", _wrap("fetch_baby_profile", fetch_baby_profile)
    )
    workflow.add_node(
        "resolve_baby_age", _wrap("resolve_baby_age", resolve_baby_age)
    )
    workflow.add_node(
        "generate_care_alerts", _wrap("generate_care_alerts", generate_care_alerts)
    )

    workflow.set_entry_point("fetch_history")
    workflow.add_edge("fetch_history", "fetch_baby_profile")
    workflow.add_edge("fetch_baby_profile", "resolve_baby_age")
    workflow.add_edge("resolve_baby_age", "generate_care_alerts")
    workflow.add_edge("generate_care_alerts", END)

    graph = workflow.compile()
    logger.info("护理留意状态图构建完成（含 thinking 编排）")
    return graph


care_alert_graph = build_care_alert_graph()
