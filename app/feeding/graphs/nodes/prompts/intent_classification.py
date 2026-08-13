"""
意图分类提示词

业务说明：
只做增删改查与闲聊/退出。注入全量事件树（标明父/叶子）。
create/update/delete 只能用叶子；read 用户说父名则只输出父 id。
字典外专名当备注，禁止新建事件。
查记录输出 unix 窗 + event_ids + remark_keyword。
叶子可带字典 type，仅帮模型选 start/end/one；不注入进行中历史。
复合切换句必须拆成 events[] 且每件自带 action。
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
    把全量树压成提示用简表：id/name/kind，父带 children 名，叶子带 parent 名。

    业务说明：
    叶子带字典 type（one|time|number），只帮模型选 start/end/one。
    不写入进行中历史或 history id，避免靠摘要打补丁。
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
            # 只列直接子名，让模型知道「换尿布」下面是尿尿/拉屎
            kids = get_children(eid, event_dictionary)
            item["children"] = [c.get("event_name") or "" for c in kids]
        else:
            # 叶子类型来自字典，不采信模型返回的 event_type
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
) -> str:
    """
    构建分类系统提示。

    注入全量树、当前上海时间，以及可选的备注探针一行摘要。
    备注探针不是进行中历史；禁止把进行中记录摘要塞进本提示。
    """
    events_simple = _events_for_prompt(event_dictionary)
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

可用事件（只能用这里的 id 和 name，禁止发明新事件；kind=parent 为分类，kind=leaf 为具体事项）：
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
5. 多事件用 events[]，最多 3 个。一句话同时停止一件并开始/记录另一件（不 X 了、改 Y 了、换成、现在不…了）必须拆成至少两项，每项自己的 action 和字典叶子 id：停止填 end，开始填 start（叶子 type=time）或 one（type=one/number）。禁止把停止与开始揉成同一项，禁止两件都标成 one 或 start。此时顶层 action=multi，op=create。
6. 无法确定则 conversation + 短 content。
7. 成长建议类闲聊用 conversation，不要 suggest。
8. create/update/delete 只能用 kind=leaf 的 id，禁止用父 id 落库。
9. read：用户说的是父名（kind=parent）时，event_id 和 event_ids 只填该父 id，不要自行展开成叶子列表。用户分别点名多个叶子时才填多个叶子 id。
10. 用户原文可能同音不同字（怕≈爬、做≈坐、该≈改）。必须对照可用事件表选语义最接近的字典真名再填 id；对不上就 missing_events 或 conversation，禁止发明列表外名称（如「怕练习」）。
11. 叶子 type 只帮助选择 start/end/one：time 用 start/end，one/number 用 one。不要返回 event_type，计时与否由系统按字典处理。
12. 只返回 JSON，不要其它文字。

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
