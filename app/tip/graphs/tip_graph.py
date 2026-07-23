"""
小贴士状态图

业务说明：
使用 LangGraph StateGraph 构建小贴士生成流程图。
包含数据需求判断→按需拉取历史→向量检索→宝宝画像→流式回答完整链路。
与 clinic_graph、intent_graph 共享 judge_data_requirement、fetch_history、search_vectors、fetch_baby_profile 节点。

设计思路：
1. 使用 TipState 定义状态（包含 event_info、baby_age_months、current_time 等小贴士特有字段）
2. 线性流程：judge → fetch_history → search_vectors → fetch_baby_profile
3. 流式回答在路由层直接调用 stream_tip_response 生成器函数
4. 编译后导出 tip_graph 实例供路由层调用

流式思考支持（astream 模式）：
本图支持 LangGraph 的 astream() 流式执行模式，路由层可调用 graph.astream() 获取每个节点的执行 chunk。
与 clinic_graph 一样，每个节点完成时推送 thinking 事件，节点全部完成后再调用 stream_tip_response 流式输出 LLM 回答。

注意：
流式回答（stream_tip_response）是生成器函数，不适合作为 StateGraph 的节点。
因此 graph 只负责数据准备，流式生成在路由层直接调用 stream_tip_response。
"""

import logging
from typing import Any, Dict

from langgraph.graph import StateGraph, END

from app.tip.graphs.states.tip_state import TipState
from app.shared.graphs.nodes.judge_data_requirement import judge_data_requirement
from app.shared.graphs.nodes.fetch_history import fetch_history
from app.shared.graphs.nodes.search_vectors import search_vectors
from app.shared.graphs.nodes.fetch_baby_profile import fetch_baby_profile

# 初始化日志记录器
logger = logging.getLogger(__name__)


def build_tip_graph() -> StateGraph:
    """
    构建小贴士状态图

    业务逻辑：
    1. 创建 StateGraph，使用 TipState
    2. 添加数据准备节点：judge_data_requirement, fetch_history, search_vectors, fetch_baby_profile
    3. 线性连接所有节点
    4. 编译并返回

    注意：
    流式回答生成不包含在 graph 中，由路由层直接调用 stream_tip_response 生成器。
    graph 只负责准备上下文数据（历史、知识、宝宝画像）。

    Returns:
        编译后的 LangGraph 图实例
    """
    # 创建 StateGraph
    workflow = StateGraph(TipState)

    # 添加节点（复用共享节点）
    workflow.add_node("judge_data_requirement", judge_data_requirement)
    workflow.add_node("fetch_history", fetch_history)
    workflow.add_node("search_vectors", search_vectors)
    workflow.add_node("fetch_baby_profile", fetch_baby_profile)

    # 设置入口点
    workflow.set_entry_point("judge_data_requirement")

    # 线性连接节点
    workflow.add_edge("judge_data_requirement", "fetch_history")
    workflow.add_edge("fetch_history", "search_vectors")
    workflow.add_edge("search_vectors", "fetch_baby_profile")
    workflow.add_edge("fetch_baby_profile", END)

    # 编译图
    graph = workflow.compile()

    logger.info("小贴士状态图构建完成")
    return graph


# 全局小贴士图实例
# 业务说明：单例模式，全局只有一个图实例，供路由层调用
tip_graph = build_tip_graph()
