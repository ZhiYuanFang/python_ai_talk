"""
事件解析末尾：用附近历史在允许集合里猜一个叶子。

业务说明：
父事件、未识别、多候选、软确认才进来。猜中打 history_guessed，不写事件说法飞轮。
猜不中则调用方保持原来的消歧或无法识别。
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from app.feeding.graphs.nodes.prompts.system import HISTORY_EVENT_GUESS_SYSTEM_PROMPT
from app.feeding.services.event_hierarchy import (
    get_descendant_leaves,
    get_leaf_events,
    is_parent_event,
)
from app.shared.feeding_history_compact import build_feeding_history_prompt_blocks
from app.shared.graphs.stream_llm_collect import stream_llm_collect
from app.shared.http_client import http_client
from app.shared.llm_client import llm_model_config_from_mapping

logger = logging.getLogger(__name__)

_RECENT_LIMIT = 20
_JSON_BLOCK = re.compile(r"\{[\s\S]*\}")


def needs_history_event_guess(
    event: Optional[Dict[str, Any]],
    *,
    fail_reason: str,
    disambiguation_leaves: List[Dict[str, Any]],
    full_events: List[Dict[str, Any]],
) -> bool:
    """唯一叶子不猜；父、未识别、多候选、软确认才猜。"""
    if disambiguation_leaves:
        return True
    if event and is_parent_event(event.get("event_id"), full_events):
        return True
    if not event and (fail_reason or "") in ("", "event_unresolved"):
        return True
    return False


def _row_event_id(row: Dict[str, Any]) -> str:
    """历史行上的事件编号。"""
    return str(row.get("eventId") or row.get("event_id") or "").strip()


def _allowed_from(
    candidates: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """候选叶子按 event_id 去重。"""
    out: Dict[str, Dict[str, Any]] = {}
    for ev in candidates or []:
        if not isinstance(ev, dict):
            continue
        eid = str(ev.get("event_id") or "").strip()
        if eid and eid not in out:
            out[eid] = ev
    return out


def _parse_choice(content: str) -> str:
    """从模型正文取出 event_id。"""
    raw = (content or "").strip()
    if not raw:
        return ""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        m = _JSON_BLOCK.search(raw)
        if not m:
            return ""
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return ""
    if not isinstance(data, dict):
        return ""
    return str(data.get("event_id") or "").strip()


async def _recent_rows(
    device_no: str,
    event_ids: Optional[List[str]],
) -> List[Dict[str, Any]]:
    """最近约二十条，忽略原话里的目标时刻。"""
    return await http_client.get_filtered_history_events(
        device_no=device_no,
        event_ids=event_ids,
        limit=_RECENT_LIMIT,
        ignore_time_range=True,
    )


async def guess_leaf_from_history(
    *,
    segment: str,
    utterance: str,
    device_no: str,
    full_events: List[Dict[str, Any]],
    llm_model: Optional[Dict[str, Any]],
    event: Optional[Dict[str, Any]],
    disambiguation_leaves: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    在允许集合内选一个叶子。

    Returns:
        带 history_guessed 的叶子副本；没猜中返回 None。
    """
    if not (device_no or "").strip():
        return None
    if disambiguation_leaves:
        allowed = _allowed_from(disambiguation_leaves)
        fetch_ids = list(allowed.keys())
    elif event and is_parent_event(event.get("event_id"), full_events):
        allowed = _allowed_from(
            get_descendant_leaves(event.get("event_id"), full_events)
        )
        fetch_ids = list(allowed.keys())
    else:
        allowed = _allowed_from(get_leaf_events(full_events))
        fetch_ids = None
    if not allowed:
        return None
    try:
        rows = await _recent_rows(device_no, fetch_ids)
    except Exception as exc:
        logger.warning("历史猜事件拉史失败: %s", exc)
        return None
    if fetch_ids is None:
        seen = {_row_event_id(r) for r in rows or [] if isinstance(r, dict)}
        allowed = {eid: ev for eid, ev in allowed.items() if eid in seen}
        if not allowed:
            return None
    lines = [
        f"{eid}\t{str(ev.get('event_name') or '').strip()}"
        for eid, ev in allowed.items()
    ]
    compact, _legend = build_feeding_history_prompt_blocks(rows or [])
    payload = (
        f"用户原话：{(utterance or segment or '').strip()}\n"
        f"本段：{(segment or '').strip()}\n"
        f"允许的叶子（event_id\\t名称）：\n" + "\n".join(lines) + "\n"
        f"最近历史：\n{compact or '（无）'}"
    )
    try:
        content = await stream_llm_collect(
            messages=[{"role": "user", "content": payload}],
            model_config=llm_model_config_from_mapping(llm_model or {}),
            system_prompt=HISTORY_EVENT_GUESS_SYSTEM_PROMPT,
            node_name="history_event_guess",
        )
    except Exception as exc:
        logger.warning("历史猜事件模型失败: %s", exc)
        return None
    chosen = _parse_choice(content or "")
    leaf = allowed.get(chosen)
    if leaf is None:
        return None
    copied = dict(leaf)
    copied["history_guessed"] = True
    logger.info(
        "历史猜中叶子: id=%s name=%s segment=%s",
        copied.get("event_id"),
        copied.get("event_name"),
        (segment or "")[:40],
    )
    return copied
