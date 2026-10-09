"""
意图分类提示词

业务说明：
只描述 JSON 字段含义与事件表约束。无顶层 op/action。
涉事件一律填 events[]，每项自带 op；闲聊/退出 events 为空。
注入全量树、当前时间、进行中计时摘要与规则预解析时间（不含 history_id）。
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List

from app.feeding.graphs.nodes.prompts.system import (
    INTENT_CLASSIFICATION_SYSTEM_TEMPLATE,
)
from app.feeding.services.closed_interval import should_degrade_partial_clock
from app.feeding.services.event_hierarchy import (
    get_children,
    get_event_by_id,
    parent_id_set,
)
from app.feeding.utils.duration_extractor import extract_duration_seconds
from app.feeding.utils.time_slot_extractor import extract_clocks_from_text
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


def build_time_preparse_hint(text: str) -> str:
    """
    组装分类用规则预解析时间短块（软参考）。

    业务说明：
    复用 clock/duration 抽取与半命中判定；输出紧凑，避免撑长提示。
    partial 时标明勿采用残缺单点；权威时间仍由确认前 apply 盖写。

    Args:
        text: 用户原文

    Returns:
        可拼进 system extra 的多行短文
    """
    clocks = extract_clocks_from_text(text or "")
    duration = extract_duration_seconds(text or "")
    partial = should_degrade_partial_clock(text or "", clocks)
    tz = shanghai_tz()
    clock_rows: List[Dict[str, Any]] = []
    for c in clocks:
        try:
            local = datetime.fromtimestamp(int(c.unix), tz=tz).strftime(
                "%Y-%m-%d %H:%M"
            )
        except (OSError, OverflowError, ValueError):
            local = ""
        clock_rows.append(
            {"raw": c.raw, "unix": int(c.unix), "local": local}
        )
    payload: Dict[str, Any] = {
        "partial": bool(partial),
        "clocks": clock_rows,
    }
    if duration is not None and duration > 0:
        payload["duration_sec"] = int(duration)
    compact = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    lines = [
        "规则预解析时间（优先参考；确认前服务端会再按规则盖写）：",
        compact,
    ]
    if not clock_rows and not payload.get("duration_sec"):
        lines.append("无规则钟点/时长；start/end 可留 0，由服务端规则补。")
    elif partial:
        lines.append("partial：勿把残缺单点当唯一权威；勿逐步推算 Unix。")
    else:
        lines.append("非 partial：start_time/end_time 优先抄 clocks[].unix；勿逐步推算 Unix。")
    return "\n".join(lines)


def build_intent_classification_system_prompt(
    event_dictionary: List[Dict[str, Any]],
    *,
    in_progress_hint: str = "",
    time_preparse_hint: str = "",
) -> str:
    """
    构建分类系统提示：字段含义 + 表约束 + 进行中 + 预解析时间。

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
    extra_parts = [
        "进行中计时（本设备当前未结束的计时叶子，用于理解用户要停哪件；"
        "不要把历史行 id 写入 JSON）：\n"
        + progress,
    ]
    preparse = (time_preparse_hint or "").strip()
    if preparse:
        extra_parts.append(preparse)
    extra = "\n\n".join(extra_parts)

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
