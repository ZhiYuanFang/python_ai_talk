"""
预测问答：双通道锚点匹配与播报文案

业务说明：
active 消费 active-eta items 的 expectEndAt；next 消费 imminent events 的 nextAt。
按段事件 id 与目录归根对齐 leaf/root/eventId。
clock / remain 分维播报；remain 超时固定「已经过了预计时间」。
无匹配时估不准，禁止回落查史「上一次…用时」。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.feeding.services.active_timing_eta import _ids_equal, _norm_id, _parse_unix_sec
from app.feeding.services.event_hierarchy import get_root_event_id
from app.shared.history_window import shanghai_tz


def _format_remain_hm(secs: int) -> str:
    """剩余秒数 → 相对时长口吻。"""
    if secs < 60:
        return "不到1分钟"
    hours, rem = divmod(secs, 3600)
    minutes = rem // 60
    if hours and minutes:
        return f"{hours}小时{minutes}分"
    if hours:
        return f"{hours}小时"
    return f"{minutes}分"


def _event_match_ids(
    event_id: str,
    full_events: List[Dict[str, Any]],
) -> Tuple[str, str]:
    """
    段事件的叶子 id 与归根 id。

    Returns:
        (leaf_or_self, root_id)
    """
    eid = _norm_id(event_id)
    if not eid:
        return "", ""
    root = get_root_event_id(eid, full_events) or eid
    return eid, root


def match_active_expect_end(
    event_id: str,
    eta_items: List[Dict[str, Any]],
    full_events: List[Dict[str, Any]],
) -> Optional[int]:
    """
    按 leafEventId → rootEventId 匹配进行中 ETA 的 expectEndAt。

    业务说明：
    无 history 行时用段事件 id 对齐；多条命中取任意有效 expectEndAt（通常一事件一条）。
    """
    if not eta_items:
        return None
    leaf, root = _event_match_ids(event_id, full_events)
    if not leaf and not root:
        return None

    # 先叶子再根，对齐 active_timing_eta 优先级
    for it in eta_items:
        if leaf and _ids_equal(leaf, it.get("leafEventId")):
            end = _parse_unix_sec(it.get("expectEndAt"))
            if end is not None:
                return end
    for it in eta_items:
        if root and _ids_equal(root, it.get("rootEventId")):
            end = _parse_unix_sec(it.get("expectEndAt"))
            if end is not None:
                return end
    # 兼容偶发只写 eventId 的项
    for it in eta_items:
        raw = it.get("eventId") or it.get("event_id")
        if leaf and _ids_equal(leaf, raw):
            end = _parse_unix_sec(it.get("expectEndAt"))
            if end is not None:
                return end
        if root and _ids_equal(root, raw):
            end = _parse_unix_sec(it.get("expectEndAt"))
            if end is not None:
                return end
    return None


def match_imminent_next_at(
    event_id: str,
    events: List[Dict[str, Any]],
    full_events: List[Dict[str, Any]],
    *,
    now: Optional[datetime] = None,
) -> Optional[int]:
    """
    按 eventId（叶/根）匹配 imminent 的 nextAt；多条取最近未来，否则取最近过去。
    """
    if not events:
        return None
    leaf, root = _event_match_ids(event_id, full_events)
    if not leaf and not root:
        return None

    candidates: List[int] = []
    for it in events:
        eid = it.get("eventId") or it.get("event_id")
        if not (
            (leaf and _ids_equal(leaf, eid))
            or (root and _ids_equal(root, eid))
        ):
            continue
        nxt = _parse_unix_sec(it.get("nextAt") or it.get("next_at"))
        if nxt is not None:
            candidates.append(nxt)
    if not candidates:
        return None

    tz = shanghai_tz()
    current = now or datetime.now(tz=tz)
    if current.tzinfo is None:
        current = current.replace(tzinfo=tz)
    else:
        current = current.astimezone(tz)
    now_ts = int(current.timestamp())
    future = sorted(n for n in candidates if n >= now_ts)
    if future:
        return future[0]
    return max(candidates)


def format_predict_answer(
    *,
    anchor_unix: int,
    time_answer: str,
    predict_channel: str,
    event_name: str = "",
    now: Optional[datetime] = None,
) -> str:
    """
    按 time_answer 生成播报文案。

    remain 超时 MUST 含「已经过了预计时间」；clock 含「预计约 HH:mm」。
    """
    tz = shanghai_tz()
    current = now or datetime.now(tz=tz)
    if current.tzinfo is None:
        current = current.replace(tzinfo=tz)
    else:
        current = current.astimezone(tz)
    now_ts = current.timestamp()
    name = (event_name or "").strip() or "这件事"
    channel = (predict_channel or "").strip().lower()
    answer = (time_answer or "").strip().lower()

    if answer == "remain":
        if now_ts > float(anchor_unix):
            return "已经过了预计时间"
        remain = int(float(anchor_unix) - now_ts)
        hm = _format_remain_hm(max(0, remain))
        if channel == "active":
            return f"大概还有{hm}结束（{name}）"
        return f"大概还有{hm}开始（{name}）"

    # clock：墙钟
    dt = datetime.fromtimestamp(int(anchor_unix), tz=tz)
    hhmm = dt.strftime("%H:%M")
    if channel == "active":
        return f"预计约 {hhmm} 结束（{name}）"
    return f"预计约 {hhmm} 开始（{name}）"


def coerce_predict_dims(
    channel: str,
    time_answer: str,
    aspect: str = "",
) -> Tuple[str, str, str, bool]:
    """
    归一预测三格。

    缺省 aspect 视为 when。amount / duration 清空 time_answer。
    返回 (channel, time_answer, aspect, 是否填满)。
    """
    pc = (channel or "").strip().lower()
    ta = (time_answer or "").strip().lower()
    asp = (aspect or "").strip().lower()
    if pc not in ("active", "next"):
        pc = ""
    if asp not in ("when", "amount", "duration"):
        # 空串是旧载荷：按何时；非法词不算填满
        if asp != "":
            return pc, "", "", False
        asp = "when"
    if asp == "when":
        if ta not in ("clock", "remain"):
            return pc, "", "when", False
        return pc, ta, "when", bool(pc)
    return pc, "", asp, bool(pc)


def predict_confirm_sentence(event_name: str, aspect: str, time_answer: str) -> str:
    """没把握时的确认句：跟着用量 / 用时 / 何时，不把用量问成还要多久。"""
    name = (event_name or "").strip() or "相关事件"
    asp = (aspect or "").strip().lower() or "when"
    ta = (time_answer or "").strip().lower()
    if asp == "amount":
        return f"您是要问「{name}」大概要多少吗？"
    if asp == "duration":
        return f"您是要问「{name}」大概要持续多久吗？"
    if ta == "clock":
        return f"您是要问「{name}」大概几点吗？"
    return f"您是要问「{name}」大概还要多久吗？"


def missing_aspect_message(event_name: str, aspect: str) -> str:
    """所问的预计用量或用时没有数时的降级，不改念另一格。"""
    name = (event_name or "").strip()
    label = "用量" if (aspect or "").strip().lower() == "amount" else "用时"
    if name:
        return f"暂时估不准「{name}」的预计{label}，请稍后再问。"
    return f"暂时估不准预计{label}，请稍后再问。"


def uncertainty_message(event_name: str = "") -> str:
    """
    无预测数据时的降级文案。

    MUST NOT 含「上一次」「用时」类查史完成句。
    """
    name = (event_name or "").strip()
    if name:
        return f"暂时估不准「{name}」的预计时间，请稍后再问。"
    return "暂时估不准预计时间，请稍后再问。"
