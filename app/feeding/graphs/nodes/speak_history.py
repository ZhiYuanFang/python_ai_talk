"""
查记录模板播报节点

业务说明：
按已定 event_ids + unix 窗 + 可选 remark 拉史，用模板填 content。
先查口头说的事件；父无记录才改用最近有记录的子，子无记录只再试父一次。
点查选行/进行中话术服从查史播报飞轮两维（point_pick / open_speak）；
缺维走小 LLM，禁止静默优先已完成。
日汇总非次数问按语境短答，未覆盖走模型并记规则缺口。
无事件编号不追问，按窗或点查最近全量后二十字猜测。
父无记录则只用最近有记录的子事件；子无记录则再试父一次。
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from app.feeding.schemas.intent_result import IntentResult, coerce_intent_result
from app.feeding.services.active_timing_eta import eta_suffix_for_row
from app.feeding.services.event_hierarchy import (
    get_descendant_leaves,
    get_event_by_id,
    is_parent_event,
)
from app.feeding.services.history_daily_context import (
    daily_context_kind,
    llm_daily_uncovered,
    llm_missing_event_guess,
    rule_answer_for_kind,
)
from app.feeding.services.history_mode_cues import (
    day_phrase_for_speak,
    is_count_query,
)
from app.feeding.services.history_speak_policy import (
    HISTORY_SPEAK_DEGRADE,
    resolve_history_speak_policy,
)
from app.feeding.services.intent_cache_store import intent_cache_store
from app.feeding.services.intent_events import coerce_ignore_time_range
from app.shared.constants import IntentOp, TargetType
from app.shared.graphs.state_patch import state_get
from app.shared.history_prompt_fields import (
    _parse_epoch,
    format_history_time,
)
from app.shared.history_window import (
    enum_to_unix,
    parse_day_word_window,
    resolve_window,
)
from app.shared.http_client import http_client

logger = logging.getLogger(__name__)


def _shanghai_now() -> datetime:
    """服务端当前时间（Asia/Shanghai）。"""
    return datetime.now(ZoneInfo("Asia/Shanghai"))


def _row_name(row: Dict[str, Any]) -> str:
    return str(row.get("eventName") or row.get("event_name") or "")


def _row_id(row: Dict[str, Any]) -> str:
    return str(row.get("eventId") or row.get("event_id") or "")


def _row_remark(row: Dict[str, Any]) -> str:
    return str(row.get("remark") or "").strip()


def _row_start_ts(row: Dict[str, Any]) -> float:
    """排序键：startTime 越近越大。"""
    dt = _parse_epoch(row.get("startTime") or row.get("start_time"))
    return dt.timestamp() if dt is not None else 0.0


def _is_in_progress_row(row: Dict[str, Any]) -> bool:
    """进行中：无有效结束时间（空 / 0 / 不可解析）。"""
    end = row.get("endTime")
    if end in (None, ""):
        end = row.get("end_time")
    if end in (None, "", 0, "0"):
        return True
    return _parse_epoch(end) is None


def _duration_seconds(row: Dict[str, Any]) -> Optional[int]:
    """计时：end-start 秒数；无效或未结束则 None。"""
    dt_s = _parse_epoch(row.get("startTime") or row.get("start_time"))
    dt_e = _parse_epoch(row.get("endTime") or row.get("end_time"))
    if dt_s is None or dt_e is None:
        return None
    secs = int((dt_e - dt_s).total_seconds())
    if secs < 0:
        return None
    return secs


def _elapsed_seconds_now(row: Dict[str, Any]) -> Optional[int]:
    """进行中已持续：now−start 秒数。"""
    dt_s = _parse_epoch(row.get("startTime") or row.get("start_time"))
    if dt_s is None:
        return None
    now = _shanghai_now()
    if dt_s.tzinfo is None:
        dt_s = dt_s.replace(tzinfo=ZoneInfo("Asia/Shanghai"))
    secs = int((now - dt_s).total_seconds())
    if secs < 0:
        return None
    return secs


def _format_only_in_progress(
    row: Dict[str, Any],
    *,
    parent_name: str = "",
    leaf_name: str = "",
    eta_items: Optional[List[Dict[str, Any]]] = None,
    full_events: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    open_speak=in_progress 时的固定话术。

    例：目前仅找到一条记录，是今天 14:11发生，正在进行中
    有匹配 ETA 时追加「，预计约 HH:mm 结束」或带「 · 已超时」。
    """
    when = (
        format_history_time(
            row.get("startTime") or row.get("start_time"),
            style="relative",
        )
        or "未知时间"
    )
    eta_part = eta_suffix_for_row(
        row, eta_items, full_events or [],
    )
    if parent_name and leaf_name:
        return (
            f"目前仅找到一条记录，是{when}发生的{leaf_name}"
            f"（{parent_name}），正在进行中{eta_part}"
        )
    return f"目前仅找到一条记录，是{when}发生，正在进行中{eta_part}"


def _format_elapsed_open(
    row: Dict[str, Any],
    *,
    name: str = "",
    parent_name: str = "",
    leaf_name: str = "",
) -> str:
    """
    open_speak=elapsed：报已持续时长（now−start）。

    例：睡眠从今天 14:11 开始，已持续约 2小时15分
    """
    when = (
        format_history_time(
            row.get("startTime") or row.get("start_time"),
            style="relative",
        )
        or "未知时间"
    )
    secs = _elapsed_seconds_now(row)
    dur = _format_duration_hm(secs) if secs is not None else "一段时间"
    if parent_name and leaf_name:
        return (
            f"{leaf_name}（{parent_name}）从{when}开始，已持续约{dur}"
        )
    label = name or leaf_name or "该记录"
    return f"{label}从{when}开始，已持续约{dur}"


def _format_open_row(
    row: Dict[str, Any],
    *,
    open_speak: str,
    name: str = "",
    parent_name: str = "",
    leaf_name: str = "",
    eta_items: Optional[List[Dict[str, Any]]] = None,
    full_events: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """按 open_speak 拼进行中行话术。"""
    if open_speak == "elapsed":
        return _format_elapsed_open(
            row,
            name=name,
            parent_name=parent_name,
            leaf_name=leaf_name,
        )
    return _format_only_in_progress(
        row,
        parent_name=parent_name,
        leaf_name=leaf_name,
        eta_items=eta_items,
        full_events=full_events,
    )


def _will_need_eta_point(
    rows: List[Dict[str, Any]],
    event_names: List[str],
    *,
    point_pick: str,
    open_speak: str,
) -> bool:
    """点查是否会走 in_progress 话术（决定是否拉 ETA）。"""
    if open_speak != "in_progress":
        return False
    by_name: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        name = _row_name(row)
        if not name:
            continue
        by_name.setdefault(name, []).append(row)
    wanted = event_names or list(by_name.keys())
    for name in wanted:
        row, is_open = _pick_point_row(by_name.get(name) or [], point_pick)
        if row and is_open:
            return True
    return False


def _will_need_eta_parent(
    rows: List[Dict[str, Any]],
    *,
    point_pick: str,
    open_speak: str,
) -> bool:
    """父塌缩是否会走 in_progress 话术。"""
    if open_speak != "in_progress":
        return False
    row, is_open = _pick_point_row(rows, point_pick)
    return bool(row and is_open)


def _pick_completed_or_only_open(
    rows: List[Dict[str, Any]],
) -> Tuple[Optional[Dict[str, Any]], bool]:
    """
    prefer_completed：取最近已完成；若无已完成则取最近进行中。

    Returns:
        (选中行, 是否进行中)
    """
    if not rows:
        return None, False
    completed = [r for r in rows if not _is_in_progress_row(r)]
    if completed:
        return max(completed, key=_row_start_ts), False
    opens = [r for r in rows if _is_in_progress_row(r)]
    if opens:
        return max(opens, key=_row_start_ts), True
    return None, False


def _pick_point_row(
    rows: List[Dict[str, Any]],
    point_pick: str,
) -> Tuple[Optional[Dict[str, Any]], bool]:
    """
    按 point_pick 选行。

    Returns:
        (选中行, 是否进行中)
    """
    if not rows:
        return None, False
    pick = (point_pick or "").strip().lower()
    if pick == "latest":
        row = max(rows, key=_row_start_ts)
        return row, _is_in_progress_row(row)
    return _pick_completed_or_only_open(rows)


def _format_duration_hm(secs: int) -> str:
    """秒数 → 用时口吻：X小时Y分 / Y分 / 不到1分钟。"""
    if secs < 60:
        return "不到1分钟"
    hours, rem = divmod(secs, 3600)
    minutes = rem // 60
    if hours and minutes:
        return f"{hours}小时{minutes}分"
    if hours:
        return f"{hours}小时"
    return f"{minutes}分"


def _lookup_event_type(
    row: Dict[str, Any],
    full_events: List[Dict[str, Any]],
) -> str:
    """
    解析 one|time|number。

    优先历史行 eventType；缺省按字典 event_type。
    """
    t = str(row.get("eventType") or row.get("event_type") or "").strip().lower()
    if t in ("number", "time", "one"):
        return t
    found = get_event_by_id(_row_id(row), full_events)
    if found:
        t2 = str(found.get("event_type") or "").strip().lower()
        if t2 in ("number", "time", "one"):
            return t2
    return "one"


def _remark_suffix(row: Dict[str, Any]) -> str:
    remark = _row_remark(row)
    return f"，备注{remark}" if remark else ""


def _format_typed_clause(
    *,
    name: str,
    row: Dict[str, Any],
    kind: str,
    when: str,
    parent_name: str = "",
) -> str:
    """
    按事件类型拼一句点查。

    叶子：上一次{名}是{相对时间}…
    父：上一次{父}的时候是{叶}，{相对时间}…
    """
    extra_remark = _remark_suffix(row)
    if parent_name:
        head = f"上一次{parent_name}的时候是{name}，{when}"
    else:
        head = f"上一次{name}是{when}"
    if kind == "time":
        secs = _duration_seconds(row)
        if secs is None:
            if parent_name:
                return f"上一次{parent_name}的时候是{name}，{when}开始的，现在正在进行中{extra_remark}"
            return f"上一次{name}是{when}开始的，现在正在进行中{extra_remark}"
        return f"{head}，用时{_format_duration_hm(secs)}{extra_remark}"
    if kind == "number":
        num = row.get("eventNumber")
        if num is None:
            num = row.get("event_number")
        if num in (None, ""):
            num = 0
        return f"{head}，数量为：{num}{extra_remark}"
    # 一次性：不带 number
    return f"{head}{extra_remark}"


def _expand_query_ids(
    event_ids: List[str],
    full_events: List[Dict[str, Any]],
) -> Tuple[List[str], List[str]]:
    """
    把父 id 展开成子孙叶子 id。

    Returns:
        (拉史用叶子 id 列表, 原始列表中的父 id)
    """
    parent_ids: List[str] = []
    query_ids: List[str] = []
    seen: set[str] = set()
    for eid in event_ids:
        if is_parent_event(eid, full_events):
            parent_ids.append(eid)
            for leaf in get_descendant_leaves(eid, full_events):
                lid = str(leaf.get("event_id") or "")
                if lid and lid not in seen:
                    seen.add(lid)
                    query_ids.append(lid)
            continue
        if eid not in seen:
            seen.add(eid)
            query_ids.append(eid)
    return query_ids, parent_ids


def _latest_single_event_rows(
    rows: List[Dict[str, Any]],
    full_events: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], str]:
    """
    多子事件混在一起时，只留时间最近的那一个事件的行。

    Returns:
        (该事件的行, 事件名)
    """
    best_id = ""
    best_ts = -1.0
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        rid = _row_id(row)
        ts = _row_start_ts(row)
        if rid and ts >= best_ts:
            best_ts = ts
            best_id = rid
    if not best_id:
        return [], ""
    scoped = [r for r in rows if isinstance(r, dict) and _row_id(r) == best_id]
    found = get_event_by_id(best_id, full_events)
    name = str((found or {}).get("event_name") or "").strip()
    return scoped, name


async def _fetch_history_ids(
    *,
    device_no: str,
    event_ids: Optional[List[str]],
    mode: str,
    start_time: Optional[int],
    end_time: Optional[int],
    limit: int,
    remark: Optional[str],
    ignore_time: bool,
) -> List[Dict[str, Any]]:
    """按模式拉史：日汇总带窗，点查忽略时间窗。"""
    if mode == "daily" and not ignore_time:
        return await http_client.get_filtered_history_events(
            device_no=device_no,
            event_ids=event_ids,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            remark=remark,
            ignore_time_range=False,
        )
    return await http_client.get_filtered_history_events(
        device_no=device_no,
        event_ids=event_ids,
        limit=limit,
        remark=remark,
        ignore_time_range=True,
    )


async def _kin_retry_rows(
    *,
    device_no: str,
    event_id: str,
    full_events: List[Dict[str, Any]],
    mode: str,
    start_time: Optional[int],
    end_time: Optional[int],
    limit: int,
    remark: Optional[str],
    ignore_time: bool,
) -> Tuple[List[Dict[str, Any]], str, bool]:
    """
    口头父子对不齐时再试一次。

    父无记录：拉全部子孙后只留最近有记录的一个子。
    子无记录：只再查父 id，不扫兄弟。

    Returns:
        (行, 用来播报的名字, 是否改用了子事件)
    """
    if is_parent_event(event_id, full_events):
        leaf_ids = [
            str(leaf.get("event_id") or "").strip()
            for leaf in get_descendant_leaves(event_id, full_events)
        ]
        leaf_ids = [x for x in leaf_ids if x]
        if not leaf_ids:
            return [], "", False
        rows = await _fetch_history_ids(
            device_no=device_no,
            event_ids=leaf_ids,
            mode=mode,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            remark=remark,
            ignore_time=ignore_time,
        )
        scoped, name = _latest_single_event_rows(rows, full_events)
        return scoped, name, bool(scoped)
    found = get_event_by_id(event_id, full_events)
    parent_id = str((found or {}).get("parent_id") or "").strip()
    if not parent_id or parent_id in ("0", "None"):
        return [], "", False
    rows = await _fetch_history_ids(
        device_no=device_no,
        event_ids=[parent_id],
        mode=mode,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        remark=remark,
        ignore_time=ignore_time,
    )
    parent = get_event_by_id(parent_id, full_events)
    name = str((parent or {}).get("event_name") or "").strip()
    return rows or [], name, False


def _template_point(
    rows: List[Dict[str, Any]],
    event_names: List[str],
    full_events: List[Dict[str, Any]],
    *,
    point_pick: str,
    open_speak: str,
    eta_items: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    多叶子分别点查：按 point_pick 选行；进行中按 open_speak 话术。
    """
    by_name: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        name = _row_name(row)
        if not name:
            continue
        by_name.setdefault(name, []).append(row)
    parts: List[str] = []
    wanted = event_names or list(by_name.keys())
    for name in wanted:
        candidates = by_name.get(name) or []
        row, is_open = _pick_point_row(candidates, point_pick)
        if not row:
            parts.append(f"没有记到{name}")
            continue
        if is_open:
            parts.append(
                _format_open_row(
                    row,
                    open_speak=open_speak,
                    name=name,
                    eta_items=eta_items,
                    full_events=full_events,
                )
            )
            continue
        when = format_history_time(
            row.get("startTime") or row.get("start_time"),
            style="relative",
        ) or "未知时间"
        kind = _lookup_event_type(row, full_events)
        parts.append(_format_typed_clause(name=name, row=row, kind=kind, when=when))
    return "。".join(parts) + "。" if parts else "没有查到相关记录。"


def _template_parent_latest(
    rows: List[Dict[str, Any]],
    parent_name: str,
    full_events: List[Dict[str, Any]],
    *,
    point_pick: str,
    open_speak: str,
    eta_items: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    父点查：按 point_pick 选行；进行中按 open_speak 并点出父/叶名。
    """
    if not rows:
        return f"没有记到{parent_name}相关记录。"
    latest, is_open = _pick_point_row(rows, point_pick)
    if not latest:
        return f"没有记到{parent_name}相关记录。"
    leaf_name = _row_name(latest) or "该记录"
    if is_open:
        return (
            _format_open_row(
                latest,
                open_speak=open_speak,
                parent_name=parent_name,
                leaf_name=leaf_name,
                eta_items=eta_items,
                full_events=full_events,
            )
            + "。"
        )
    when = format_history_time(
        latest.get("startTime") or latest.get("start_time"),
        style="relative",
    ) or "未知时间"
    kind = _lookup_event_type(latest, full_events)
    return (
        _format_typed_clause(
            name=leaf_name,
            row=latest,
            kind=kind,
            when=when,
            parent_name=parent_name,
        )
        + "。"
    )


async def _answer_without_event(
    state: Any,
    intent: Dict[str, Any],
    full_events: List[Dict[str, Any]],
    mode: str,
) -> str:
    """
    整段没有事件编号：按已解析窗拉全类型，二十字内猜测。

    点查或窗无效时只取最近若干条，避免无界全量。
    不写事件说法飞轮。
    """
    del full_events
    device_no = state_get(state, "device_no") or ""
    user_text = state_get(state, "user_input") or ""
    llm_model = (
        state_get(state, "llm_model") or state_get(state, "model_config") or {}
    )
    if not isinstance(llm_model, dict):
        llm_model = {}
    req = {
        "start_time": intent.get("start_time") or intent.get("startTime"),
        "end_time": intent.get("end_time") or intent.get("endTime"),
        "time_range": intent.get("time_range"),
    }
    start_time, end_time = resolve_window(req)
    ignore_time = coerce_ignore_time_range(intent.get("ignore_time_range"))
    if (
        mode == "daily"
        and not ignore_time
        and start_time is None
        and end_time is None
    ):
        filled = parse_day_word_window(user_text)
        if filled is None and is_count_query(user_text):
            filled = enum_to_unix("today")
        if filled is not None:
            start_time, end_time = filled
    bounded = mode == "daily" and not ignore_time and start_time is not None
    try:
        rows = await _fetch_history_ids(
            device_no=device_no,
            event_ids=None,
            mode=mode,
            start_time=start_time,
            end_time=end_time,
            limit=50 if bounded else 20,
            remark=None,
            ignore_time=not bounded,
        )
    except Exception as exc:
        logger.error("无事件拉史失败: %s", exc, exc_info=True)
        rows = []
    return await llm_missing_event_guess(
        utterance=str(user_text),
        rows=rows or [],
        device_no=device_no,
        llm_model=llm_model,
    )


async def speak_history(state: Any) -> Dict[str, Any]:
    """按 events[].op=read 各自时间窗拉史并模板播报。"""
    from app.feeding.services.intent_events import (
        has_read_events,
        normalize_intent_events,
    )

    intent = coerce_intent_result(state_get(state, "intent_result")).to_plain_dict()
    intent = normalize_intent_events(intent)
    tt = str(intent.get("target_type") or "").lower()
    rs = str(intent.get("read_source") or "").lower()
    is_record = tt == TargetType.HISTORY.value or (
        tt == TargetType.READ.value and rs in ("record", "")
    )
    if not has_read_events(intent) and not is_record:
        return {}
    device_no = state_get(state, "device_no") or ""
    full_events = (
        state_get(state, "event_dictionary_full")
        or state_get(state, "event_dictionary")
        or []
    )
    read_items = [
        e
        for e in (intent.get("events") or [])
        if isinstance(e, dict)
        and str(e.get("op") or "").strip().lower() == IntentOp.READ.value
    ]
    # 兼容：无 read 子项但 target=history 时，用顶层投影
    if not read_items:
        event_ids = intent.get("event_ids") or []
        if not event_ids and intent.get("event_id"):
            event_ids = [intent.get("event_id")]
        for eid in event_ids:
            if eid in (None, ""):
                continue
            read_items.append(
                {
                    "op": IntentOp.READ.value,
                    "event_id": str(eid),
                    "event_name": intent.get("event_name") or "",
                    "start_time": intent.get("start_time"),
                    "end_time": intent.get("end_time"),
                    "remark": intent.get("remark") or "",
                }
            )
    if not read_items:
        # 无事件：按已解析窗拉全量；点查或无界则最近若干条，禁止无条件全量
        content = await _answer_without_event(
            state,
            intent,
            full_events,
            mode=(intent.get("history_mode") or "point").strip().lower(),
        )
        intent["content"] = content
        return {
            "intent_result": IntentResult.model_validate(intent),
            "response": content,
        }

    user_text = state_get(state, "user_input") or ""
    mode = (intent.get("history_mode") or "point").strip().lower()
    # 点查策略两维：飞轮或 LLM；日汇总未覆盖语境也要用同一模型配置
    point_pick = ""
    open_speak = ""
    llm_model = (
        state_get(state, "llm_model")
        or state_get(state, "model_config")
        or {}
    )
    if not isinstance(llm_model, dict):
        llm_model = {}
    if mode != "daily":
        policy = await resolve_history_speak_policy(str(user_text), llm_model)
        if policy is None:
            content = HISTORY_SPEAK_DEGRADE
            intent["content"] = content
            logger.warning("查史播报策略解析失败，降级话术")
            return {
                "intent_result": IntentResult.model_validate(intent),
                "response": content,
            }
        point_pick, open_speak = policy
        logger.info(
            "查史播报策略: pick=%s open=%s text=%s",
            point_pick,
            open_speak,
            str(user_text)[:40],
        )

    id_to_name = {
        str(e.get("event_id")): e.get("event_name") or "" for e in full_events
    }
    parts: List[str] = []
    all_rows: List[Dict[str, Any]] = []
    cache_events: List[Dict[str, Any]] = []
    # 本轮设备级 ETA：未拉过为 None；拉过后为 list（可空）；仅 in_progress 话术时拉取
    eta_items_cache: Optional[List[Dict[str, Any]]] = None

    async def _ensure_eta_items() -> List[Dict[str, Any]]:
        """仅 in_progress 播报时拉一次 active-eta；失败降级为空列表。"""
        nonlocal eta_items_cache
        if eta_items_cache is not None:
            return eta_items_cache
        try:
            eta_items_cache = await http_client.get_predict_active_eta(device_no)
        except Exception as exc:
            logger.warning(
                "进行中 ETA 拉取失败，降级无 ETA: device_no=%s err=%s",
                device_no,
                exc,
            )
            eta_items_cache = []
        return eta_items_cache

    for item in read_items:
        eid = str(item.get("event_id") or "").strip()
        name = str(item.get("event_name") or id_to_name.get(eid) or "").strip()
        remark = str(
            item.get("remark")
            or intent.get("remark")
            or state_get(state, "remark")
            or ""
        ).strip()
        req = {
            "start_time": item.get("start_time")
            if item.get("start_time") not in (None, 0, "0")
            else intent.get("start_time") or intent.get("startTime"),
            "end_time": item.get("end_time")
            if item.get("end_time") not in (None, 0, "0")
            else intent.get("end_time") or intent.get("endTime"),
            "time_range": intent.get("time_range"),
        }
        start_time, end_time = resolve_window(req)
        # LLM 判定「上一次」时为 true → 透传 Go ignoreTimeRange，避免猜测窗踩空
        ignore_time = coerce_ignore_time_range(item.get("ignore_time_range"))
        # daily 且窗无效：按原文日词补窗（和昨天比→两日，勿无界拉史）
        if (
            mode == "daily"
            and not ignore_time
            and start_time is None
            and end_time is None
        ):
            filled = parse_day_word_window(user_text)
            if filled is None and is_count_query(user_text):
                # 几次类无日词：默认今天（注释见 design）
                filled = enum_to_unix("today")
            if filled is not None:
                start_time, end_time = filled
                logger.info(
                    "daily 日词补窗: start=%s end=%s text=%s",
                    start_time,
                    end_time,
                    user_text[:40],
                )
        original_ids = [eid] if eid else []
        if not original_ids:
            # 无事件编号：按窗拉全类型；点查或无界只取最近若干条
            try:
                rows = await _fetch_history_ids(
                    device_no=device_no,
                    event_ids=None,
                    mode=mode,
                    start_time=start_time,
                    end_time=end_time,
                    limit=50 if mode == "daily" and start_time is not None else 20,
                    remark=remark or None,
                    ignore_time=ignore_time
                    or mode != "daily"
                    or start_time is None,
                )
            except Exception as exc:
                logger.error(f"无事件拉史失败: {exc}", exc_info=True)
                rows = []
            parts.append(
                await llm_missing_event_guess(
                    utterance=user_text,
                    rows=rows or [],
                    device_no=device_no,
                    llm_model=llm_model,
                )
            )
            continue
        # 先只查口头说的 id，空了再做亲属再试
        fetch_ids = [eid]
        # daily 区段默认提高 limit，降低一周/多日被 20 条截断
        _DAILY_DEFAULT_LIMIT = 50
        if intent.get("limit") not in (None, "", 0, "0"):
            try:
                fetch_limit = int(intent.get("limit"))
            except (TypeError, ValueError):
                fetch_limit = _DAILY_DEFAULT_LIMIT if mode == "daily" else 20
        else:
            fetch_limit = _DAILY_DEFAULT_LIMIT if mode == "daily" else 20
        try:
            rows = await _fetch_history_ids(
                device_no=device_no,
                event_ids=fetch_ids,
                mode=mode,
                start_time=start_time,
                end_time=end_time,
                limit=fetch_limit,
                remark=remark or None,
                ignore_time=ignore_time,
            )
        except Exception as exc:
            logger.error(f"查记录拉史失败: {exc}", exc_info=True)
            parts.append(f"{name or '该事件'}暂时没查到，请稍后再试。")
            continue
        collapse_parent = is_parent_event(eid, full_events)
        if not rows:
            try:
                kin_rows, kin_name, used_child = await _kin_retry_rows(
                    device_no=device_no,
                    event_id=eid,
                    full_events=full_events,
                    mode=mode,
                    start_time=start_time,
                    end_time=end_time,
                    limit=fetch_limit,
                    remark=remark or None,
                    ignore_time=ignore_time,
                )
            except Exception as exc:
                logger.warning("亲属再试拉史失败: %s", exc)
                kin_rows, kin_name, used_child = [], "", False
            if kin_rows:
                rows = kin_rows
                if kin_name:
                    name = kin_name
                if used_child:
                    collapse_parent = False
        all_rows.extend(rows or [])
        parent_ids = [eid] if collapse_parent else []
        if mode == "daily":
            # 次数问：显式 N 次（number 叶不得只报总量）
            if is_count_query(user_text):
                n = len(rows or [])
                day_zh = day_phrase_for_speak(user_text)
                ev = name or "该事件"
                if n <= 0:
                    chunk = f"{day_zh}{ev}没有相关记录"
                else:
                    chunk = f"{day_zh}{ev}{n}次"
            else:
                # 非次数：预设语境短答；对不上则模型并记规则缺口
                kind = daily_context_kind(user_text)
                if kind:
                    chunk = rule_answer_for_kind(kind, rows or [], name)
                elif not rows:
                    chunk = f"{name or '这段时间'}没有相关记录。"
                else:
                    chunk = await llm_daily_uncovered(
                        utterance=user_text,
                        rows=rows or [],
                        device_no=device_no,
                        llm_model=llm_model,
                    )
        elif collapse_parent:
            parent_name = name or id_to_name.get(parent_ids[0], "") or "该分类"
            etas: Optional[List[Dict[str, Any]]] = None
            if _will_need_eta_parent(
                rows or [],
                point_pick=point_pick,
                open_speak=open_speak,
            ):
                etas = await _ensure_eta_items()
            chunk = _template_parent_latest(
                rows or [],
                str(parent_name),
                full_events,
                point_pick=point_pick,
                open_speak=open_speak,
                eta_items=etas,
            )
        else:
            names = [name] if name else [id_to_name.get(str(x), "") for x in original_ids]
            names = [n for n in names if n]
            etas = None
            if _will_need_eta_point(
                rows or [],
                names,
                point_pick=point_pick,
                open_speak=open_speak,
            ):
                etas = await _ensure_eta_items()
            chunk = _template_point(
                rows or [],
                names,
                full_events,
                point_pick=point_pick,
                open_speak=open_speak,
                eta_items=etas,
            )
        parts.append(chunk.rstrip("。"))
        # 缓存快照保留 ignore_time_range，命中后点查行为一致
        cache_events.append(
            {
                "op": IntentOp.READ.value,
                "event_id": eid,
                "event_name": name,
                "remark": remark,
                "start_time": start_time,
                "end_time": end_time,
                "ignore_time_range": ignore_time,
            }
        )

    content = "。".join(parts) + ("。" if parts else "")
    if not content:
        content = "没有查到相关记录。"
    # 回填 segment_text：cache_events 无原文时从拼装 events 按 event_id 取
    seg_by_id = {
        str(e.get("event_id") or "").strip(): str(e.get("segment_text") or "").strip()
        for e in (intent.get("events") or [])
        if isinstance(e, dict) and e.get("event_id")
    }
    intent["content"] = content
    intent["events"] = cache_events or intent.get("events") or []
    # 仅对拉史成功的段写短说法（失败段不写；不依赖 leaf_confirm）
    full = state_get(state, "event_dictionary_full") or []
    for ev in cache_events:
        if not isinstance(ev, dict):
            continue
        eid = str(ev.get("event_id") or "").strip()
        if not eid:
            continue
        seg = str(ev.get("segment_text") or "").strip() or seg_by_id.get(eid, "")
        ename = str(ev.get("event_name") or "").strip()
        doc = seg or ename
        if not doc:
            continue
        kind = "parent" if is_parent_event(eid, full) else "leaf"
        intent_cache_store.add_event_phrase(
            doc, event_id=eid, event_name=ename, kind=kind
        )
    logger.info(f"查记录模板: {content[:80]}")
    return {
        "intent_result": IntentResult.model_validate(intent),
        "response": content,
        "history_events": all_rows,
    }

