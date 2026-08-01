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
    # clinic：隐式判定上一条建议是否被接受（飞轮）
    "implicit_feedback": "正在回想咱们刚聊到的建议...",
    # 数据需求判断：是否需要拉喂养史当背景
    "judge_data_requirement": "正在看看要不要翻翻最近的记录...",
    # 历史拉取：Go 侧喂养记录
    "fetch_history": "正在翻翻最近的喂养记录...",
    # 向量检索：知识背景
    "search_vectors": "正在想想有没有相关经验可以参考...",
    # 宝宝画像
    "fetch_baby_profile": "正在了解宝宝的基本情况...",
    # tip：自算月龄
    "derive_baby_age": "正在根据生日算算宝宝月龄...",
    # 开始生成口语回复
    "llm_start": "正在想怎么跟你说...",
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
