"""
意图分类提示词

业务说明：
只描述 JSON 字段含义与事件表约束。不把用户话术关键字绑到某个 op。
注入全量树、当前时间与进行中计时摘要（不含 history_id）。
备注反查在分类后由规则完成，不在此注入备注摘要。
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
    表内活动可简称/进行态对真名；表外专名不得凭常识升格成类别。
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
- 表中事件的type属性决定action的值，type=one时action=one，type=time时action=start|end，type=number时action=end。

字段含义：
- op：create=留下新记录或开始计时；read=查看已有记录；update=修改已有记录的内容或结束计时；delete=去掉已有记录；空=闲聊或退出
- target_type：feeding(CUD事件) | history(R事件) | conversation(闲聊) | exit(退出)
- action：start=计时类型的事件开始|end=非一次性类型的事件结束|one=一次性类型的事件记录|multi=含有多个事件|search=查询事件|reply=闲聊|exit=退出
- event_name / event_id：能对上表时填表内名称与 id；对不上时 event_name 保留用户词、event_id 空
- events：一句话涉及多件时每件一项，每项自带 action 与叶子 id/name
- event_ids / start_time / end_time：read 时填写；时间为 Unix 秒，按用户语义估算时间窗
- quantity：数量，没有则 null
- content：闲聊短句，CRUD 可空

表约束：
- 禁止编造不在表中的 event_id；
- create/update/delete 只作用与 kind=leaf 的 事件
- read 可作用于kind=parent的事件
- 只返回 JSON，不要其它文字

JSON 格式(不可添加注释，保障json格式正确)：
{{
  "op": "create|read|update|delete|",
  "target_type": "feeding|history|conversation|exit",
  "action": "start|end|one|multi|search|reply|exit",
  "event_name": "表内事件名或用户原词或空",
  "event_id": "已有事件ID或空",
  "event_ids": ["read 时的事件ID"],
  "start_time": 0,
  "end_time": 0,
  "remark_keyword": "备注专名，没有则空",
  "quantity": null,
  "events": [{{"action": "one", "event_name": "", "event_id": "", "quantity": null}}],
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
