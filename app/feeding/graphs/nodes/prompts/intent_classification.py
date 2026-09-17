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

from app.feeding.graphs.nodes.prompts.system import (
    INTENT_CLASSIFICATION_SYSTEM_TEMPLATE,
)
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

    return INTENT_CLASSIFICATION_SYSTEM_TEMPLATE.format(
        now_line=now_line,
        event_str=event_str,
        extra=extra,
    )


def build_intent_classification_user_message(text: str) -> str:
    """构建分类用户消息。"""
    return f"""
请分析以下用户输入，识别意图：

用户输入：{text}
"""
