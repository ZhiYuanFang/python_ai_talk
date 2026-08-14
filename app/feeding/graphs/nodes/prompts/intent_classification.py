"""
意图分类提示词

业务说明：
只描述 JSON 字段含义与事件表约束。无顶层 op/action。
涉事件一律填 events[]，每项自带 op；闲聊/退出 events 为空。
注入全量树、当前时间与进行中计时摘要（不含 history_id）。
"""

import json
from datetime import datetime
from typing import Any, Dict, List

from app.feeding.services.event_hierarchy import (
    get_children,
    get_event_by_id,
    parent_id_set,
)
from app.shared.history_window import shanghai_tz


def _events_for_prompt(event_dictionary: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    把全量树压成提示用简表：id/name/kind，父带 children 名，叶子带 parent 名与 type。
    """
    parents = parent_id_set(event_dictionary)
    simple: List[Dict[str, Any]] = []
    for event in event_dictionary:
        eid = str(event.get("event_id", event.get("id", "")) or "")
        if not eid:
            continue
        name = event.get("event_name", "") or ""
        kind = "parent" if eid in parents else "leaf"
        item: Dict[str, Any] = {"id": eid, "name": name, "kind": kind}
        if kind == "parent":
            kids = get_children(eid, event_dictionary)
            item["children"] = [c.get("event_name") or "" for c in kids]
        else:
            et = str(event.get("event_type") or "").strip().lower()
            if et in ("one", "time", "number"):
                item["type"] = et
        pid = event.get("parent_id")
        if pid not in (None, ""):
            parent = get_event_by_id(pid, event_dictionary)
            item["parent"] = (parent or {}).get("event_name") or ""
        simple.append(item)
    return simple


def build_intent_classification_system_prompt(
    event_dictionary: List[Dict[str, Any]],
    *,
    in_progress_hint: str = "",
) -> str:
    """
    构建分类系统提示：字段含义 + 表约束 + 进行中数据。

    不写用户句式或同音对照。进行中摘要不含 history id。
    """
    events_simple = _events_for_prompt(event_dictionary)
    event_str = json.dumps(events_simple, ensure_ascii=False, indent=2)
    tz = shanghai_tz()
    now_dt = datetime.now(tz=tz)
    now_line = (
        f"当前时间：{now_dt.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    progress = (in_progress_hint or "").strip() or "当前无进行中计时。"
    extra = (
        "进行中计时（本设备当前未结束的计时叶子，用于理解用户要停哪件；"
        "不要把历史行 id 写入 JSON）：\n"
        + progress
    )

    return f"""
你是事件意图分析助手。根据语义按JSON格式返回结果。
{now_line}

可用事件仅包含这些（禁止编造 id）：
{event_str}

{extra}

名称对齐原则：
- 用户说的是表内已有事件或简称时，必须填表内真名与 id。
- 表里没有的事件，不得凭常识改写成某个类别事件，此时 event_name 保持用户原词，event_id 留空。
- 叶子 type=one 时子项 action 用 one；type=time 开始用 start、结束用 end；type=number 记录用 one 或按语义。

字段含义：
- target_type：feeding(对事件增删改结束) | history(读取事件) | conversation(闲聊) | exit(退出)
- events：涉事件时必填数组；每项自带 op 与叶子 id/name。单事件也是长度为 1 的数组。闲聊与退出 events 必须为 []。
- events[].op：create=留下新记录或开始计时；end=结束进行中计时（不是 update）；update=修改已有记录内容；delete=去掉已有记录；read=查看已有记录
- events[].action：可选；create 时 start|one；end 时可为 end；update/delete/read 可空
- events[].start_time / end_time：op=read 时填写该子项自己的时间窗（Unix 秒）
- events[].remark_keyword：该子项查记录备注专名，没有则空或不写
- events[].quantity：数量，没有则 null
- content：闲聊短句；feeding/history 可空
- 不要输出顶层 op、不要输出顶层 action

表约束：
- 禁止编造不在表中的 event_id
- create/update/delete/end 只作用于 kind=leaf
- read 可作用于 kind=parent 或 leaf
- feeding 时 events 非空且 op 为 create|update|delete|end
- history 时 events 非空且含 op=read，每项尽量自带时间窗
- conversation / exit 时 events 为 []
- 只输出纯 JSON，不包含任何其他文字、解释、问候语
- JSON 内部不得包含任何注释（//、/* */、# 等均不允许）
- 时间的使用不需要解释来源，避免json格式错误

JSON 格式：
{{
  "target_type": "feeding|history|conversation|exit",
  "events": [
    {{
      "op": "create|update|delete|end|read",
      "action": "start|one|end|",
      "event_name": "表内事件名或用户原词或空",
      "event_id": "已有事件ID或空",
      "quantity": null,
      "start_time": 0,
      "end_time": 0,
      "remark_keyword": ""
    }}
  ],
  "need_confirm": true,
  "confirm_message": "需要确认时的问句",
  "content": "闲聊短句，CRUD 可空"
}}
"""


def build_intent_classification_user_message(text: str) -> str:
    """构建分类用户消息。"""
    return f"""
请分析以下用户输入，识别意图：

用户输入：{text}
"""
