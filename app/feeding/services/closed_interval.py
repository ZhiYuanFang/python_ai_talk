"""
计时闭合区间槽位合并

业务说明：
根据原文 clock / duration，为 create 子项填写 start_time/end_time（闭合补记），
或单点开表。供 overlay_slots 与落库前共用，避免仅缓存路径生效。
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from app.feeding.utils.duration_extractor import extract_duration_seconds
from app.feeding.utils.quantity_extractor import extract_quantities_from_text
from app.feeding.utils.time_slot_extractor import ClockHint, extract_clocks_from_text
from app.shared.constants import IntentAction, IntentOp

logger = logging.getLogger(__name__)

# 起止连接词（增强信号；两 clock 单条时即使无连接词也按起止）
_RANGE_JOIN_RE = re.compile(r"到|至|～|~|—|–|-")


def should_degrade_multi_clock(text: str, clocks: List[ClockHint], events: List[Dict]) -> bool:
    """
    是否因多钟点强制降级 LLM。

    业务说明：
    ≥3 钟点且单条 → 降级；恰好 2 钟点按起止，不降级。
    """
    if len(events) != 1:
        return False
    return len(clocks) >= 3


def apply_time_slots_to_events(
    text: str,
    events: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], bool]:
    """
    将钟点/时长/数量盖到 events 副本上。

    Returns:
        (新 events, 是否有变更)
    """
    if not events:
        return events, False
    clocks = extract_clocks_from_text(text)
    duration = extract_duration_seconds(text)
    qtys = extract_quantities_from_text(text)
    out = [dict(e) for e in events if isinstance(e, dict)]
    if not out:
        return events, False
    changed = False
    n = len(out)
    now = int(time.time())

    # 单条 create：闭合 / 开表优先
    if n == 1:
        ev = out[0]
        op = str(ev.get("op") or "").strip().lower()
        if op == IntentOp.CREATE.value:
            closed = _apply_closed_or_open(ev, clocks, duration, now, text)
            if closed:
                changed = True
            # 闭合后不再用单 clock 把 end 抹成 start
        # 数量（与闭合独立）
        if qtys:
            ev["quantity"] = qtys[0]
            changed = True
        return out, changed

    # 多条：按序 zip clock/qty（不起止合并）
    for i, ev in enumerate(out):
        op = str(ev.get("op") or "").strip().lower()
        if i < len(clocks):
            ev["start_time"] = clocks[i].unix
            if op == IntentOp.CREATE.value:
                action = str(ev.get("action") or "").strip().lower()
                if action != IntentAction.START.value:
                    # 非显式 start：瞬时对齐；若有 duration 仅盖到首条在上面单条分支
                    ev["end_time"] = clocks[i].unix
            changed = True
        if i < len(qtys):
            ev["quantity"] = qtys[i]
            changed = True
    return out, changed


def _apply_closed_or_open(
    ev: Dict[str, Any],
    clocks: List[ClockHint],
    duration: Optional[int],
    now: int,
    text: str,
) -> bool:
    """
    单条 create：写入闭合区间或单点开始。

    Returns:
        是否改写了时间字段
    """
    changed = False
    # 双钟点起止
    if len(clocks) == 2:
        a, b = clocks[0].unix, clocks[1].unix
        start_u, end_u = (a, b) if a <= b else (b, a)
        ev["start_time"] = start_u
        ev["end_time"] = end_u
        ev["action"] = IntentAction.ONE.value
        logger.info(
            "闭合起止: start=%s end=%s range_join=%s",
            start_u,
            end_u,
            bool(_RANGE_JOIN_RE.search(text or "")),
        )
        return True
    # 时长 + 0/1 钟点
    if duration and duration > 0:
        if len(clocks) == 1:
            start_u = clocks[0].unix
            end_u = start_u + duration
        else:
            end_u = now
            start_u = now - duration
        ev["start_time"] = start_u
        ev["end_time"] = end_u
        ev["action"] = IntentAction.ONE.value
        logger.info("闭合时长: start=%s end=%s dur=%s", start_u, end_u, duration)
        return True
    # 单钟点、无时长：开始时刻；end 留给 collect（计时开表 / 瞬时对齐）
    if len(clocks) == 1:
        ev["start_time"] = clocks[0].unix
        # 不写 end_time，计时由 collect 开表；若 action 已是 one 非计时则 collect 用 start
        action = str(ev.get("action") or "").strip().lower()
        if action and action != IntentAction.START.value:
            # 瞬时事件：end=start
            ev["end_time"] = clocks[0].unix
        changed = True
    return changed
