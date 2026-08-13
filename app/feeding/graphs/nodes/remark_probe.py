"""
分类前探针：备注模糊 + 进行中计时摘要

业务说明：
缓存未命中时拉近窗历史，筛进行中计时注入分类（不含 history_id）。
用户词不在字典时再打备注模糊，一行摘要供分类把专名对到已有事件。
不把原始行列表注入 prompt。是否查询由 LLM 按字段含义判断，不用本地句式正则。
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.feeding.services.event_hierarchy import get_event_by_id
from app.shared.history_window import enum_to_unix, shanghai_tz
from app.shared.http_client import http_client

logger = logging.getLogger(__name__)

# 剥掉常见虚词，剩下的当备注专名候选（不是判断查/删）
_STRIP_RE = re.compile(
    r"上一次|上次|最近一次|什么时候|啥时候|何时|吃的|喝的|吃了|喝了|"
    r"查一下|查查|分别|是|的|了|呢|吗|呀|啊|\s+",
)


def extract_oov_token(text: str, event_names: List[str]) -> Optional[str]:
    """抽出不在字典里的专名候选。"""
    t = (text or "").strip()
    leftover = _STRIP_RE.sub("", t)
    leftover = leftover.strip("？?。．.!！，,、")
    if not leftover or len(leftover) > 20:
        return None
    names = {n.strip() for n in event_names if n and n.strip()}
    if leftover in names:
        return None
    for n in names:
        if leftover in n or n in leftover:
            return None
    return leftover


def _summarize_hits(rows: List[Dict[str, Any]], keyword: str) -> str:
    """聚合成一行：事件名 × 次数，最近时间。"""
    names: List[str] = []
    latest = ""
    for row in rows:
        name = str(row.get("eventName") or row.get("event_name") or "")
        if name:
            names.append(name)
        if not latest:
            latest = str(row.get("startTime") or row.get("start_time") or "")
    if not names:
        return f"备注含 {keyword}：近窗无命中"
    counts = Counter(names)
    parts = [f"{n} ×{c}" for n, c in counts.most_common()]
    extra = f"，最近 {latest}" if latest else ""
    return f"备注含 {keyword}：{'、'.join(parts)}{extra}"


def _is_open_end(row: Dict[str, Any]) -> bool:
    """结束时间为空或 0 视为进行中。"""
    raw = row.get("endTime")
    if raw is None:
        raw = row.get("end_time")
    if raw in (None, "", 0, "0"):
        return True
    try:
        return int(raw) == 0
    except (TypeError, ValueError):
        return False


def _row_event_id(row: Dict[str, Any]) -> str:
    return str(row.get("eventId") or row.get("event_id") or "").strip()


def _fmt_start(raw: Any) -> str:
    """Unix 秒格式化为上海墙钟，供提示阅读；失败则原样。"""
    try:
        ts = int(raw)
    except (TypeError, ValueError):
        return str(raw or "")
    if ts <= 0:
        return ""
    return datetime.fromtimestamp(ts, tz=shanghai_tz()).strftime("%Y-%m-%d %H:%M")


def summarize_in_progress(
    rows: List[Dict[str, Any]],
    full_events: List[Dict[str, Any]],
) -> str:
    """
    进行中计时压成提示用一行列表。

    只收字典 event_type=time 且未结束的叶子。不含 history id。
    """
    by_eid: Dict[str, Dict[str, Any]] = {}
    for row in rows or []:
        if not _is_open_end(row):
            continue
        eid = _row_event_id(row)
        if not eid:
            continue
        leaf = get_event_by_id(eid, full_events)
        if not leaf:
            continue
        if str(leaf.get("event_type") or "").strip().lower() != "time":
            continue
        prev = by_eid.get(eid)
        start = row.get("startTime") or row.get("start_time") or 0
        if prev is None:
            by_eid[eid] = {"leaf": leaf, "start": start}
            continue
        try:
            if int(start or 0) >= int(prev.get("start") or 0):
                by_eid[eid] = {"leaf": leaf, "start": start}
        except (TypeError, ValueError):
            by_eid[eid] = {"leaf": leaf, "start": start}
    if not by_eid:
        return "当前无进行中计时。"
    lines = ["当前进行中计时："]
    for eid, item in by_eid.items():
        name = item["leaf"].get("event_name") or eid
        when = _fmt_start(item.get("start"))
        extra = f" 开始于 {when}" if when else ""
        lines.append(f"- {name} id={eid}{extra}")
    return "\n".join(lines)


async def _fetch_recent_rows(device_no: str) -> List[Dict[str, Any]]:
    """近窗小页历史，供进行中筛选。"""
    start_time, end_time = enum_to_unix("last_30_days")
    return await http_client.get_filtered_history_events(
        device_no=device_no,
        event_ids=None,
        start_time=start_time,
        end_time=end_time,
        limit=20,
    )


async def remark_probe(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    分类前探针：进行中摘要必做；备注仅在抽出字典外词时请求。

    缓存已命中则跳过。
    """
    if state.get("intent_cache_hit"):
        return {}
    text = state.get("user_input") or ""
    device_no = state.get("device_no") or ""
    full_events = (
        state.get("event_dictionary_full") or state.get("event_dictionary") or []
    )
    in_progress_hint = "当前无进行中计时。"
    try:
        recent = await _fetch_recent_rows(device_no)
        in_progress_hint = summarize_in_progress(recent or [], full_events)
    except Exception as exc:
        logger.warning(f"进行中探针失败: {exc}")
        in_progress_hint = "当前无进行中计时。"

    dictionary = state.get("event_dictionary") or []
    names = [str(e.get("event_name") or "") for e in dictionary]
    # 全量树名字也参与 OOV 判断，避免父名被当成备注
    names.extend(str(e.get("event_name") or "") for e in full_events)
    token = extract_oov_token(text, names)
    if not token:
        logger.info(f"进行中探针: {in_progress_hint[:80]}")
        return {
            "remark_probe_hint": "",
            "in_progress_hint": in_progress_hint,
        }
    start_time, end_time = enum_to_unix("last_30_days")
    try:
        rows = await http_client.get_filtered_history_events(
            device_no=device_no,
            event_ids=None,
            start_time=start_time,
            end_time=end_time,
            limit=10,
            remark=token,
        )
    except Exception as exc:
        logger.warning(f"备注探针失败: {exc}")
        return {
            "remark_probe_hint": "",
            "remark_keyword": token,
            "in_progress_hint": in_progress_hint,
        }
    hint = _summarize_hits(rows or [], token)
    logger.info(f"备注探针: token={token}, hint={hint}; 进行中={in_progress_hint[:80]}")
    return {
        "remark_probe_hint": hint,
        "remark_keyword": token,
        "in_progress_hint": in_progress_hint,
    }
