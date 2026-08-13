"""
意图图节点思考文案映射表

业务说明：
定义意图分析（intent_graph）中各节点执行时对应的中文字幕（thinking 事件内容）。
用于 feeding 模块意图分析流的流式思考展示，让用户实时感知 AI 正在做什么。

设计思路：
1. 集中维护节点名→中文文案的映射，便于统一管理和后续扩展
2. 提供 get_thinking_message 函数，传入节点名返回对应文案
3. 未知节点返回通用文案，保证不会出现空内容
"""

# 节点名→中文思考文案映射表
# 业务说明：每个 key 对应意图图中注册的节点名，value 为推送给前端的中文文案
NODE_THINKING_MESSAGES = {
    "match_intent_cache": "正在回忆你常说的话...",
    "remark_probe": "正在查看当前记录...",
    "classify_intent": "正在分析你的意图...",
    "execute_history_crud": "正在写入喂养记录...",
    "speak_history": "正在整理历史记录...",
    "llm_start": "正在生成回答...",
}


def get_thinking_message(node_name: str) -> str:
    """
    根据节点名获取对应的中文思考文案

    业务逻辑：
    1. 查找映射表，命中则返回对应文案
    2. 未命中则返回通用文案，避免前端收到空内容

    Args:
        node_name: 意图图中注册的节点名

    Returns:
        该节点对应的中文字幕文案
    """
    # 从映射表查找，找不到时返回通用文案
    return NODE_THINKING_MESSAGES.get(
        node_name,
        f"正在处理..."  # 通用兜底文案，适用于未来新增的未知节点
    )
