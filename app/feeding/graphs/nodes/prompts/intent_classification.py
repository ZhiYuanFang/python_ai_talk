"""
意图分类提示词

业务说明：
只做增删改查与闲聊/退出。只匹配已有叶子。字典外专名当备注，禁止新建事件。
查记录输出 unix 窗 + event_ids + remark_keyword。
"""

import json
from datetime import datetime
from typing import Any, Dict, List

from app.shared.history_window import now_unix, shanghai_tz


def build_intent_classification_system_prompt(
    event_dictionary: List[Dict[str, Any]],
    *,
    remark_probe_hint: str = "",
) -> str:
    """
    构建分类系统提示。

    注入叶子字典、当前上海时间，以及可选的备注探针一行摘要。
    """
    events_simple = [
        {"id": e.get("event_id", e.get("id", "")), "name": e.get("event_name", "")}
        for e in event_dictionary
    ]
    event_str = json.dumps(events_simple, ensure_ascii=False, indent=2)
    tz = shanghai_tz()
    now_dt = datetime.now(tz=tz)
    now_line = (
        f"当前时间（Asia/Shanghai）：{now_dt.strftime('%Y-%m-%d %H:%M:%S')}，"
        f"unix={now_unix()}"
    )
    probe_block = ""
    if (remark_probe_hint or "").strip():
        probe_block = f"\n备注探针摘要（这是本设备历史，不是常识）：\n{remark_probe_hint.strip()}\n"

    return f"""
你是母婴喂养意图分析助手。只判断用户要增、删、改、查已有喂养记录，或闲聊/退出。
{now_line}

可用事件（只能用这里的 id 和 name，禁止发明新事件）：
{event_str}
{probe_block}
操作 op：
- create：记录/开始/结束一件或多件已有事件
- read：查询历史（上次/什么时候/多少/今天吃了什么）
- update：修改已有记录
- delete：删除已有记录
- 空：conversation 或 exit

规则：
1. 名称不在可用列表中 → 不是新事件。记事件时放入 missing_events 并说明；查记录时当作备注关键词 remark_keyword，event_ids 填探针或常识对应的已有事件（如 AD→营养品）。
2. 禁止 is_new_event=true，禁止编造不在列表里的 event_id。
3. 查记录必须给 event_ids（已有 id 列表）和 start_time/end_time（Unix 秒）。「上一次」用近 90 天到现在。
4. 有备注探针时，必须用探针里的事件名，确认话术用字典真名，不要把 AD 当成事件名。
5. 多事件用 events[]，最多 3 个。
6. 无法确定则 conversation + 短 content。
7. 成长建议类闲聊用 conversation，不要 suggest。
8. 只返回 JSON，不要其它文字。

JSON 格式：
{{
  "op": "create|read|update|delete|",
  "target_type": "feeding|history|conversation|exit",
  "action": "start|end|one|multi|search|reply|exit",
  "event_name": "已有事件名或空",
  "event_id": "已有事件ID或空",
  "event_ids": ["查记录时的事件ID"],
  "start_time": 0,
  "end_time": 0,
  "remark_keyword": "如 AD，没有则空",
  "quantity": null,
  "events": [{{"action": "one", "event_name": "", "event_id": "", "quantity": null}}],
  "missing_events": [],
  "need_confirm": true,
  "confirm_message": "需要确认时的问句",
  "keywords": [],
  "content": "闲聊短句，CRUD 可空"
}}
"""


def build_intent_classification_user_message(text: str) -> str:
    """构建分类用户消息。"""
    return f"""
请分析以下用户输入，识别意图：

用户输入：{text}
"""
