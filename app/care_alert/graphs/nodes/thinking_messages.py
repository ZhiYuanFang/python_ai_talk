"""
护理留意节点思考文案

业务说明：
节点名 → 中文编排字幕；经 with_node_thinking 推送。
"""

NODE_THINKING_MESSAGES = {
    "fetch_history": "正在翻翻近两天的喂养记录…",
    "fetch_baby_profile": "正在了解宝宝的基本情况…",
    "resolve_baby_age": "正在根据生日算算宝宝月龄…",
    "generate_care_alerts": "正在对照月龄期望，整理今日值得留意…",
}


def get_thinking_message(node_name: str) -> str:
    """按节点名取编排字幕；未知节点给通用文案。"""
    return NODE_THINKING_MESSAGES.get(node_name, "正在分析…")
