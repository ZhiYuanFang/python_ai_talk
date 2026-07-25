"""
意图分析图定义

业务说明：
使用 LangGraph 定义意图分析的状态图，协调向量匹配、意图分类、用户确认、
历史查询短链与 clinic agent 调用等节点。

设计思路：
1. 向量匹配 → 按置信度路由（高置信 END / 中置信确认 / 低置信 LLM）
2. LLM 分类后按 target_type 分支：feeding 确认、history 短链、conversation/suggest clinic、exit END
3. 真实 prepare_confirm（interrupt）→ handle_feedback → END
4. MemorySaver 检查点支持 Command(resume) 恢复确认流
"""

import logging
from typing import Any, Dict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END

from app.clinic.graphs.nodes.generate_response import generate_response
from app.feeding.graphs.nodes.call_clinic_agent import call_clinic_agent
from app.feeding.graphs.nodes.classify_intent import classify_intent
from app.feeding.graphs.nodes.handle_feedback import handle_feedback
from app.feeding.graphs.nodes.match_event_by_vector import match_event_by_vector
from app.feeding.graphs.nodes.prepare_confirm import prepare_confirm
from app.feeding.graphs.states.intent_state import IntentState
from app.shared.graphs.nodes.fetch_history import fetch_history
from app.shared.graphs.nodes.judge_data_requirement import judge_data_requirement

# 初始化日志记录器
logger = logging.getLogger(__name__)

# 使用 IntentState TypedDict，确保 conversation_id / user_input 等通道在检查点中保留
State = IntentState


def _route_after_vector_match(state: State) -> str:
    """
    向量匹配后的路由决策

    业务逻辑：
    1. 从状态中读取向量匹配结果和置信度
    2. 根据 match_source 和 need_confirm 决定路由：
       - match_source 为 "llm" 时，降级至 LLM 分类
       - need_confirm 为 True 时，路由到用户确认节点
       - 否则直接结束（高置信度向量匹配）

    Args:
        state: 当前图状态

    Returns:
        下一个节点的名称（"classify_intent"、"prepare_confirm" 或 "end"）
    """
    # 从状态顶层读取 match_source（向量匹配节点返回在 state 顶层）
    match_source = state.get("match_source", "llm")
    need_confirm = state.get("need_confirm", False)

    logger.info(
        f"向量匹配后路由决策: match_source={match_source}, "
        f"need_confirm={need_confirm}"
    )

    if match_source == "llm":
        return "classify_intent"
    elif need_confirm is True:
        return "prepare_confirm"
    else:
        return "end"


def _route_after_classify(state: State) -> str:
    """
    意图分类后的路由决策

    业务逻辑：
    按 intent_result.target_type 进入后处理：
    - feeding（含 multi）：进入确认
    - history：历史短链
    - conversation / suggest：clinic agent
    - exit / 其他：直接结束

    Args:
        state: 当前图状态

    Returns:
        下一跳路由键
    """
    intent_result = state.get("intent_result") or {}
    target_type = intent_result.get("target_type", "conversation")

    logger.info(f"意图分类后路由决策: target_type={target_type}")

    if target_type == "feeding":
        return "prepare_confirm"
    if target_type == "history":
        return "judge_data_requirement"
    if target_type in ("conversation", "suggest"):
        return "call_clinic_agent"
    # exit 及其他未知类型直接结束
    return "end"


def build_intent_graph() -> StateGraph:
    """
    构建意图分析图

    业务逻辑：
    1. 创建 StateGraph 实例并注册全部节点
    2. 向量匹配条件路由 + classify 后按 target_type 分支
    3. 确认边：prepare_confirm → handle_feedback → END
    4. history 短链：judge → fetch_history → generate_response → END
    5. conversation/suggest：call_clinic_agent → END
    6. 使用 MemorySaver 编译以支持 interrupt/resume

    Returns:
        编译后的 StateGraph 实例
    """
    # 创建图
    graph = StateGraph(State)

    # 添加节点
    graph.add_node("match_event_by_vector", match_event_by_vector)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("prepare_confirm", prepare_confirm)
    graph.add_node("handle_feedback", handle_feedback)
    graph.add_node("judge_data_requirement", judge_data_requirement)
    graph.add_node("fetch_history", fetch_history)
    graph.add_node("generate_response", generate_response)
    graph.add_node("call_clinic_agent", call_clinic_agent)

    # 添加入口边
    graph.add_edge(START, "match_event_by_vector")

    # 向量匹配后的条件路由
    graph.add_conditional_edges(
        "match_event_by_vector",
        _route_after_vector_match,
        {
            "classify_intent": "classify_intent",
            "prepare_confirm": "prepare_confirm",
            "end": END,
        },
    )

    # 意图分类后按 target_type 分支
    graph.add_conditional_edges(
        "classify_intent",
        _route_after_classify,
        {
            "prepare_confirm": "prepare_confirm",
            "judge_data_requirement": "judge_data_requirement",
            "call_clinic_agent": "call_clinic_agent",
            "end": END,
        },
    )

    # 确认流：interrupt 恢复后始终进入反馈处理再结束
    graph.add_edge("prepare_confirm", "handle_feedback")
    graph.add_edge("handle_feedback", END)

    # history 短链
    graph.add_edge("judge_data_requirement", "fetch_history")
    graph.add_edge("fetch_history", "generate_response")
    graph.add_edge("generate_response", END)

    # conversation / suggest
    graph.add_edge("call_clinic_agent", END)

    logger.info("意图分析图构建完成（含 MemorySaver 检查点）")

    # 编译时挂载内存检查点，使 interrupt()/Command(resume) 可按 thread_id 恢复
    return graph.compile(checkpointer=MemorySaver())


# 模块级单例：构建并导出意图分析图实例
# 供 api/routes/intent.py 等模块直接 import 使用
intent_graph = build_intent_graph()
