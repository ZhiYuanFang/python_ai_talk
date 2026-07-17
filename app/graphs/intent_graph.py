"""
意图分析状态图

业务说明：
使用 LangGraph StateGraph 构建意图分析流程图。
包含意图分类→条件路由→后处理的完整链路。
- feeding/conversation/exit 意图：直接返回，不做后处理
- history 意图：判断数据需求→拉取历史→生成回答
- suggest 意图：判断数据需求→拉取历史→向量检索→宝宝画像→生成建议

设计思路：
1. 使用 TypedDict 定义 State
2. 条件边根据 intent_result.target_type 路由到不同分支
3. 共享节点从 nodes/ 目录导入
4. 编译后导出 graph 实例供路由层调用
"""

import logging
from typing import Any, Dict

from langgraph.graph import StateGraph, END

from app.graphs.states.intent_state import IntentState
from app.graphs.nodes.classify_intent import classify_intent
from app.graphs.nodes.judge_data_requirement import judge_data_requirement
from app.graphs.nodes.fetch_history import fetch_history
from app.graphs.nodes.search_vectors import search_vectors
from app.graphs.nodes.fetch_baby_profile import fetch_baby_profile
from app.graphs.nodes.generate_response import generate_response

# 初始化日志记录器
logger = logging.getLogger(__name__)


def _route_by_intent(state: Dict[str, Any]) -> str:
    """
    意图路由函数（条件边）

    业务逻辑：
    根据意图分类结果中的 target_type 决定下一个节点。
    - feeding/conversation/exit: 直接结束（返回给 Go 侧处理或兜底）
    - history: 走历史查询后处理链路
    - suggest: 走建议生成后处理链路
    - 其他: 默认结束

    Args:
        state: 当前图状态

    Returns:
        下一个节点的名称
    """
    intent_result = state.get("intent_result", {})
    target_type = intent_result.get("target_type", "conversation")

    if target_type == "feeding":
        # 喂养意图：直接返回，Go 侧处理 CRUD
        return "end"
    elif target_type == "conversation":
        # 对话意图：直接返回兜底文案
        return "end"
    elif target_type == "exit":
        # 退出意图：直接返回
        return "end"
    elif target_type == "history":
        # 历史查询意图：走后处理
        return "judge_data_requirement"
    elif target_type == "suggest":
        # 建议意图：走完整后处理链路
        return "judge_data_requirement"
    else:
        # 未知意图：直接结束
        return "end"


def _route_after_judge(state: Dict[str, Any]) -> str:
    """
    数据需求判断后的路由函数

    业务逻辑：
    判断完成后，根据意图类型决定后续流程。
    history 直接去拉历史，suggest 还要走向量检索和宝宝画像。

    Args:
        state: 当前图状态

    Returns:
        下一个节点的名称
    """
    intent_result = state.get("intent_result", {})
    target_type = intent_result.get("target_type", "history")

    if target_type == "suggest":
        return "fetch_history"
    else:
        # history 意图：拉取历史后直接生成回答
        return "fetch_history"


def _route_after_history(state: Dict[str, Any]) -> str:
    """
    历史拉取后的路由函数

    业务逻辑：
    history 意图：拉完历史直接生成回答
    suggest 意图：还要继续向量检索和获取宝宝画像

    Args:
        state: 当前图状态

    Returns:
        下一个节点的名称
    """
    intent_result = state.get("intent_result", {})
    target_type = intent_result.get("target_type", "history")

    if target_type == "suggest":
        return "search_vectors"
    else:
        # history 意图：直接生成回答
        return "generate_response"


def build_intent_graph() -> StateGraph:
    """
    构建意图分析状态图

    业务逻辑：
    1. 创建 StateGraph，使用 IntentState
    2. 添加所有节点
    3. 设置入口点为 classify_intent
    4. 添加条件边：根据意图类型路由
    5. 添加 history 分支：judge → fetch_history → generate_response
    6. 添加 suggest 分支：judge → fetch_history → search → baby → generate_response
    7. 编译并返回

    Returns:
        编译后的 LangGraph 图实例
    """
    # 创建 StateGraph
    workflow = StateGraph(IntentState)

    # 添加节点
    workflow.add_node("classify_intent", classify_intent)
    workflow.add_node("judge_data_requirement", judge_data_requirement)
    workflow.add_node("fetch_history", fetch_history)
    workflow.add_node("search_vectors", search_vectors)
    workflow.add_node("fetch_baby_profile", fetch_baby_profile)
    workflow.add_node("generate_response", generate_response)

    # 设置入口点
    workflow.set_entry_point("classify_intent")

    # 添加条件边：意图分类后路由
    workflow.add_conditional_edges(
        "classify_intent",
        _route_by_intent,
        {
            "end": END,
            "judge_data_requirement": "judge_data_requirement",
        },
    )

    # 数据需求判断 → 拉取历史（history 和 suggest 都走这一步）
    workflow.add_edge("judge_data_requirement", "fetch_history")

    # 添加条件边：历史拉取后路由
    workflow.add_conditional_edges(
        "fetch_history",
        _route_after_history,
        {
            "generate_response": "generate_response",
            "search_vectors": "search_vectors",
        },
    )

    # suggest 分支：向量检索 → 获取宝宝画像 → 生成回答
    workflow.add_edge("search_vectors", "fetch_baby_profile")
    workflow.add_edge("fetch_baby_profile", "generate_response")

    # 生成回答 → 结束
    workflow.add_edge("generate_response", END)

    # 编译图
    graph = workflow.compile()

    logger.info("意图分析状态图构建完成")
    return graph


# 全局意图分析图实例
# 业务说明：单例模式，全局只有一个图实例，供路由层调用
intent_graph = build_intent_graph()
