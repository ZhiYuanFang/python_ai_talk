"""
节点思考文案映射表

业务说明：
定义 LangGraph 图中各节点执行时对应的中文字幕（thinking 事件内容）。
用于 clinic_graph 和 tip_graph 的流式思考展示，让用户实时感知 AI 正在做什么。

设计思路：
1. 集中维护节点名→中文文案的映射，便于统一管理和国际化
2. 提供 get_thinking_message 函数，传入节点名返回对应文案
3. 未知节点返回通用文案，保证不会出现空内容
"""

from typing import Optional

# 节点名→中文思考文案映射表
# 业务说明：每个 key 对应 LangGraph 图中注册的节点名，value 为推送给前端的中文文案
NODE_THINKING_MESSAGES = {
    # 数据需求判断节点：LLM 分析用户问题，判断需要哪些事件类型和时间范围
    "judge_data_requirement": "正在分析需要哪些历史数据...",
    # 历史拉取节点：根据数据需求判断结果，调用 Go 侧 API 拉取历史喂养记录
    "fetch_history": "正在拉取最近的喂养记录...",
    # 向量检索节点：从 Chroma 向量库中检索与当前问题相关的母婴知识
    "search_vectors": "正在检索知识库中的相关知识...",
    # 宝宝画像获取节点：调用设备服务获取宝宝基本信息（月龄、性别等）
    "fetch_baby_profile": "正在获取宝宝画像信息...",
    # LLM 回答开始标记：数据准备完成，开始调用 LLM 生成回答
    "llm_start": "正在生成回答...",
}


def get_thinking_message(node_name: str) -> str:
    """
    根据节点名获取对应的中文思考文案

    业务逻辑：
    1. 查找映射表，命中则返回对应文案
    2. 未命中则返回通用文案，避免前端收到空内容

    Args:
        node_name: LangGraph 图中注册的节点名

    Returns:
        该节点对应的中文字幕文案
    """
    # 从映射表查找，找不到时返回通用文案
    return NODE_THINKING_MESSAGES.get(
        node_name,
        f"正在处理..."  # 通用兜底文案，适用于未来新增的未知节点
    )
