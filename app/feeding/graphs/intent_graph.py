"""
意图分析图定义

业务说明：
使用 LangGraph 定义意图分析的状态图，协调向量匹配、意图分类、
历史查询短链与 clinic agent 调用等节点。

确认/消歧改为同一 /intent + conversation_id 的 pending 自由文本续聊，
图内不再使用 prepare_confirm interrupt 与 /intent/confirm。

设计思路：
1. 向量匹配 → 按置信度路由（高置信 END / 中置信 END 由路由 pending / 低置信 LLM）
2. LLM 分类后按 target_type 分支：feeding END（路由后处理）、history 短链、conversation/suggest clinic、exit END
"""

import logging
from typing import Any, Dict

from langgraph.graph import StateGraph, START, END

from app.clinic.graphs.nodes.generate_response import generate_response
from app.feeding.graphs.nodes.call_clinic_agent import call_clinic_agent
from app.feeding.graphs.nodes.classify_intent import classify_intent
from app.feeding.graphs.nodes.match_event_by_vector import match_event_by_vector
from app.feeding.graphs.states.intent_state import IntentState
from app.shared.graphs.nodes.fetch_history import fetch_history
from app.shared.graphs.nodes.judge_data_requirement import judge_data_requirement

# 初始化日志记录器
logger = logging.getLogger(__name__)

# 使用 IntentState TypedDict，确保 conversation_id / user_input 等通道保留
State = IntentState


def _route_after_vector_match(state: State) -> str:
    """
    向量匹配后的路由决策

    业务逻辑：
    - match_source 为 llm：降级至 LLM 分类
    - 否则 END（含高置信直接结果、中置信 need_confirm，由路由层 pending 处理）
    """
    match_source = state.get("match_source", "llm")
    need_confirm = state.get("need_confirm", False)

    logger.info(
        f"向量匹配后路由决策: match_source={match_source}, "
        f"need_confirm={need_confirm}"
    )

    if match_source == "llm":
        return "classify_intent"
    return "end"


def _route_after_classify(state: State) -> str:
    """
    意图分类后的路由决策

    - feeding（含 multi）：END，由路由层做叶子校验/消歧/软确认
    - history：历史短链
    - conversation / suggest：clinic agent
    - exit / 其他：直接结束
    """
    intent_result = state.get("intent_result") or {}
    target_type = intent_result.get("target_type", "conversation")

    logger.info(f"意图分类后路由决策: target_type={target_type}")

    if target_type == "feeding":
        return "end"
    if target_type == "history":
        return "judge_data_requirement"
    if target_type in ("conversation", "suggest"):
        return "call_clinic_agent"
    return "end"


def build_intent_graph() -> StateGraph:
    """
    构建意图分析图（无旧 confirm interrupt 主路径）。
    """
    graph = StateGraph(State)

    graph.add_node("match_event_by_vector", match_event_by_vector)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("judge_data_requirement", judge_data_requirement)
    graph.add_node("fetch_history", fetch_history)
    graph.add_node("generate_response", generate_response)
    graph.add_node("call_clinic_agent", call_clinic_agent)

    graph.add_edge(START, "match_event_by_vector")

    graph.add_conditional_edges(
        "match_event_by_vector",
        _route_after_vector_match,
        {
            "classify_intent": "classify_intent",
            "end": END,
        },
    )

    graph.add_conditional_edges(
        "classify_intent",
        _route_after_classify,
        {
            "end": END,
            "judge_data_requirement": "judge_data_requirement",
            "call_clinic_agent": "call_clinic_agent",
        },
    )

    graph.add_edge("judge_data_requirement", "fetch_history")
    graph.add_edge("fetch_history", "generate_response")
    graph.add_edge("generate_response", END)
    graph.add_edge("call_clinic_agent", END)

    logger.info("意图分析图构建完成（pending 澄清由 /intent 路由处理）")
    return graph.compile()


# 模块级单例
intent_graph = build_intent_graph()
