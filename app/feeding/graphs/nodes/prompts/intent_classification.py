"""
意图分类提示词

业务说明：
只描述 JSON 字段含义与事件表约束。不把用户话术关键字绑到某个 op。
注入全量树、当前时间、可选备注摘要与进行中计时摘要（不含 history_id）。
"""

import json
from datetime import datetime
from typing import Any, Dict, List

from app.feeding.services.event_hierarchy import (
    get_children,
    get_event_by_id,
    parent_id_set,
)
from app.shared.history_window import now_unix, shanghai_tz


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
    remark_probe_hint: str = "",
    in_progress_hint: str = "",
) -> str:
    """
    构建分类系统提示：字段含义 + 表约束 + 本轮数据。

    不写用户句式或同音对照。进行中摘要不含 history id。
    """
    events_simple = _events_for_prompt(event_dictionary)
    event_str = json.dumps(events_simple, ensure_ascii=False, indent=2)
    tz = shanghai_tz()
    now_dt = datetime.now(tz=tz)
    now_line = (
        f"当前时间（Asia/Shanghai）：{now_dt.strftime('%Y-%m-%d %H:%M:%S')}，"
        f"unix={now_unix()}"
    )
    extra_blocks: List[str] = []
    if (remark_probe_hint or "").strip():
        extra_blocks.append(
            "备注探针摘要（本设备历史，不是常识）：\n"
            + remark_probe_hint.strip()
        )
    progress = (in_progress_hint or "").strip() or "当前无进行中计时。"
    extra_blocks.append(
        "进行中计时（本设备当前未结束的计时叶子，用于理解用户要停哪件；"
        "不要把历史行 id 写入 JSON）：\n"
        + progress
    )
    extra = "\n\n".join(extra_blocks)

    return f"""
你是母婴喂养意图分析助手。根据用户语义填写 JSON：增、删、改、查已有喂养记录，或闲聊/退出。
{now_line}

可用事件（只能用这里的 id 和 name，禁止编造；kind=parent 为分类，kind=leaf 为可落库事项；叶子 type 只帮助选择 start/end/one）：
{event_str}

{extra}

字段含义：
- op：create=留下新记录或开始/结束计时；read=查看已有记录；update=修改已有记录的内容；delete=去掉已有记录；空=闲聊或退出
- target_type：feeding | history | conversation | exit，与 op 对应
- action：create 时 start=开始计时、end=结束计时、one=记一次、multi=events 多于一项；read 用 search；闲聊 reply；退出 exit
- event_name / event_id：表内名称与 id
- events：一句话涉及多件时每件一项，每项自带 action 与叶子 id/name，最多 3 个
- event_ids / start_time / end_time：read 时填写；时间为 Unix 秒，按用户语义估算时间窗
- remark_keyword：用户说的词不在事件表、但是某条记录的备注；此时 event_ids 用表内事件
- missing_events：要对表记账但表里没有的名称
- quantity：数量，没有则 null
- content：闲聊短句，CRUD 可空

表约束：
- 禁止编造不在表中的 event_id 或事件名；禁止 is_new_event=true
- create/update/delete 只用 kind=leaf 的 id
- read 时若用户说的是父名，event_id 与 event_ids 只填该父 id，不要自行展开成叶子
- 不要返回 event_type；不要填写 history_id
- 只返回 JSON，不要其它文字

JSON 格式：
{{
  "op": "create|read|update|delete|",
  "target_type": "feeding|history|conversation|exit",
  "action": "start|end|one|multi|search|reply|exit",
  "event_name": "已有事件名或空",
  "event_id": "已有事件ID或空",
  "event_ids": ["read 时的事件ID"],
  "start_time": 0,
  "end_time": 0,
  "remark_keyword": "备注专名，没有则空",
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
