"""
成长轨迹节点思考文案

业务说明：
节点名 → 中文编排字幕；经 with_node_thinking 推送（段首 \\r 由 emit_thinking 处理）。
"""

# 节点名→中文思考文案
NODE_THINKING_MESSAGES = {
    "fetch_history": "正在翻翻近期喂养记录（有则参考）...",
    "fetch_baby_profile": "正在了解宝宝的基本情况...",
    "resolve_baby_age": "正在根据生日算算宝宝月龄...",
    "confirm_prior": "正在对照你上次的反馈...",
    "plan_next": "正在想想还缺哪些关键信息...",
    "ask_question": "正在准备下一个问题...",
    "reconfirm": "刚才的选择有点不确定，正在再确认一下...",
    "final_free_text": "信息还不太够，这是最后一次补充提问...",
    "generate": "正在整理未来几天的成长轨迹预测...",
}


def get_thinking_message(node_name: str) -> str:
    """按节点名取编排字幕；未知节点给通用文案。"""
    return NODE_THINKING_MESSAGES.get(node_name, "正在处理...")
