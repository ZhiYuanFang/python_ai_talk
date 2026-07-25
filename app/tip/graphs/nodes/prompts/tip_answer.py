"""
小贴士回答提示词构建模块

业务说明：
构建小贴士场景回答生成节点使用的系统提示词和用户消息。
与诊疗提示词不同，小贴士针对"单次事件触发"场景，输出当下总结和下一步注意事项。

设计思路：
1. 结合当前触发事件、Asia/Shanghai 当前时间、自算宝宝月龄作为核心上下文
2. 融合知识库参考和近期喂养历史记录参考
3. 输出针对当前事件的当下总结和下一步注意事项
4. 篇幅精炼（比诊疗短），适合小贴士组件 200px 高度展示
5. 无月龄时文案为「未知」，不得写成「0 个月」伪装
"""

import json
import time
from typing import Any, Dict, List, Optional

from app.tip.graphs.nodes.derive_baby_age import shanghai_now


def build_tip_answer_system_prompt() -> str:
    """
    构建小贴士回答的系统提示词

    业务逻辑：
    引导 LLM 作为育儿助手，针对当前触发事件生成即时小贴士。
    与诊疗提示词的区别：
    1. 聚焦"当前事件"而非"用户提问"
    2. 输出更精炼（适合小贴士组件展示）
    3. 包含"当下总结"和"下一步注意事项"两个部分

    Returns:
        系统提示词字符串
    """
    return """
你是一个专业的育儿助手，擅长根据宝宝当前的事件触发场景，提供即时的小贴士建议。

请根据当前触发的事件、宝宝月龄、当前时间、近期喂养历史和知识库参考，生成一段小贴士。

输出要求：
1. 内容分为两部分：当下总结 + 下一步注意事项
2. 篇幅精炼，总计不超过 200 字
3. 语气温暖、鼓励，避免让家长焦虑
4. 建议要具体可操作，基于提供的历史和知识
5. 不要给出药物剂量或处方建议
6. 若月龄为「未知」，不要假设新生儿或 0 个月

输出格式：
## 当下总结
（针对当前事件的简短总结，1-2 句话）

## 下一步注意事项
- 注意事项 1
- 注意事项 2
（2-3 条具体建议）
"""


def format_tip_age_text(baby_age_months: Optional[int]) -> str:
    """
    将内部月龄表示转为提示词文案。

    业务逻辑：
    - None → 「宝宝月龄：未知」
    - 非负整数（含算出的 0）→ 「宝宝月龄：{n} 个月」

    Args:
        baby_age_months: 自算月龄，或 None 表示未知

    Returns:
        提示词用月龄行
    """
    if baby_age_months is None:
        return "宝宝月龄：未知"
    return f"宝宝月龄：{baby_age_months} 个月"


def build_tip_answer_user_message(
    event_info: Dict[str, Any],
    baby_age_months: Optional[int],
    history_events: List[Dict[str, Any]],
    knowledge_results: List[Dict[str, Any]],
    baby_profile: Dict[str, Any],
) -> str:
    """
    构建小贴士回答的用户消息

    业务逻辑：
    将当前事件、上海时区时间、月龄、历史记录和知识库参考组合成用户消息。
    当前时间在本函数内用 Asia/Shanghai 生成，不依赖请求体。

    Args:
        event_info: 触发事件信息，包含 event_id 和 event_name
        baby_age_months: 自算月龄；None 表示未知
        history_events: 近期喂养历史记录列表
        knowledge_results: 向量检索结果列表
        baby_profile: 宝宝画像信息

    Returns:
        用户消息字符串
    """
    # 格式化当前事件信息
    event_name = event_info.get("event_name", "未知事件")
    event_id = event_info.get("event_id", "")
    event_info_text = f"""
当前触发事件：
- 事件名称：{event_name}
- 事件ID：{event_id}
"""

    # 写提示词时生成 Asia/Shanghai 可读时间，并附 Unix 秒
    now = shanghai_now()
    local_str = now.strftime("%Y-%m-%d %H:%M:%S")
    unix_sec = int(time.time())
    age_line = format_tip_age_text(baby_age_months)
    time_age_text = f"""
当前时间：{local_str}（Asia/Shanghai）
当前时间 Unix 秒：{unix_sec}
{age_line}
"""

    # 格式化宝宝画像（性别字段兼容 sex / gender）
    baby_info = ""
    if baby_profile:
        baby_info = f"""
宝宝信息：
- 生日：{baby_profile.get("birthday", "未知")}
- 性别：{baby_profile.get("sex") or baby_profile.get("gender", "未知")}
"""

    # 格式化历史记录（只取最近 5 条，小贴士不需要太多历史）
    history_info = ""
    if history_events:
        recent_events = history_events[-5:]
        history_info = f"""
近期喂养记录：
{json.dumps(recent_events, ensure_ascii=False, indent=2)}
"""

    # 格式化知识库参考（当前检索不按月龄过滤；未知月龄时文案不写「同月龄」以免误导）
    knowledge_info = ""
    if knowledge_results:
        knowledge_texts = [f"- {r['content']}" for r in knowledge_results]
        knowledge_label = (
            "知识库参考（同月龄宝宝）"
            if baby_age_months is not None
            else "知识库参考（不限月龄）"
        )
        knowledge_info = f"""
{knowledge_label}：
{"\n".join(knowledge_texts)}
"""

    return f"""
{event_info_text}

{time_age_text}

{baby_info}

{history_info}

{knowledge_info}

请根据以上信息，针对当前"{event_name}"事件，生成一段小贴士（当下总结 + 下一步注意事项）。
"""
