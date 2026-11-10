"""
预测问答：双通道锚点匹配与播报文案

业务说明：
active 消费 active-eta 的 expectEndAt 与预计用量/时长；无正结束仍可识别进行中。
next 消费 imminent 的 nextAt 与预计用量/时长；可选 parentEventName 供根名反推。
按段事件 id 与目录归根对齐 leaf/root/eventId；MUST NOT 依赖 expectLeafTitle。
clock / remain 分维播报；remain 超时固定「已经过了预计时间」。
无匹配时估不准，禁止回落查史「上一次…用时」。
对齐 Go predict-merge-predict-contract：parentEventName 仅 pending。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.feeding.services.active_timing_eta import _ids_equal, _norm_id, _parse_unix_sec
from app.feeding.services.event_hierarchy import get_event_by_id, get_root_event_id
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


def read_parent_event_name(item: Dict[str, Any]) -> str:
    """
    读 imminent pending 可选 parentEventName（Go 契约）。

    trim 后空视为无父；不读 parentEventId / expectLeafTitle。
    """
    if not isinstance(item, dict):
        return ""
    for key in ("parentEventName", "parent_event_name"):
        raw = item.get(key)
        if raw in (None, ""):
            continue
        name = str(raw).strip()
        if name:
            return name
    return ""


def pending_speak_name(item: Dict[str, Any], fallback: str = "") -> str:
    """
    pending/active 播报名：优先 title，否则 fallback。

    MUST NOT 使用 expectLeafTitle。
    """
    if isinstance(item, dict):
        title = str(item.get("title") or "").strip()
        if title:
            return title
    return (fallback or "").strip()


def catalog_event_name(event_id: str, full_events: List[Dict[str, Any]]) -> str:
    """目录权威 event_name；找不到则空串。"""
    found = get_event_by_id(event_id, full_events)
    if not found:
        return ""
    return str(found.get("event_name") or "").strip()


def read_positive_expect_end(item: Dict[str, Any]) -> Optional[int]:
    """
    读正 expectEndAt（unix 秒）。

    省略 / null / 0 / 非正 → None（无预计结束，与 Go 一致）。
    """
    if not isinstance(item, dict):
        return None
    return _parse_unix_sec(item.get("expectEndAt"))


def match_active_expect_end(
    event_id: str,
    eta_items: List[Dict[str, Any]],
    full_events: List[Dict[str, Any]],
) -> Optional[int]:
    """
    按 leafEventId → rootEventId 匹配进行中 ETA 的正 expectEndAt。

    业务说明：
    先命中整条再取正结束；无正结束返回 None（调用方可用 match_active_item 做进行中降级）。
    不读 parentEventName（active-eta 无该字段）。
    """
    item = match_active_item(event_id, eta_items, full_events)
    if not item:
        return None
    return read_positive_expect_end(item)


def read_expect_duration_sec(item: Dict[str, Any]) -> Optional[int]:
    """
    从 Go 条目读取预计时长（秒）。

    依次看 expectDurationSec、expect_duration_sec、expectDuration。0 或空视为没有。
    """
    if not isinstance(item, dict):
        return None
    for key in ("expectDurationSec", "expect_duration_sec", "expectDuration"):
        raw = item.get(key)
        if raw in (None, ""):
            continue
        try:
            sec = int(float(raw))
        except (TypeError, ValueError):
            continue
        if sec > 0:
            return sec
    return None


def read_expect_amount(item: Dict[str, Any]) -> Optional[float]:
    """
    从 Go 条目读取预计用量。

    依次看 expectAmount、expect_amount。0 或空视为没有。
    """
    if not isinstance(item, dict):
        return None
    for key in ("expectAmount", "expect_amount"):
        raw = item.get(key)
        if raw in (None, ""):
            continue
        try:
            amount = float(raw)
        except (TypeError, ValueError):
            continue
        if amount > 0:
            return amount
    return None


def read_expect_unit(item: Dict[str, Any]) -> str:
    """预计用量的单位。没有则空串。"""
    if not isinstance(item, dict):
        return ""
    for key in ("expectUnit", "expect_unit", "unit"):
        raw = item.get(key)
        if raw not in (None, ""):
            return str(raw).strip()
    return ""


def _active_id_rank(item: Dict[str, Any], leaf: str, root: str) -> int:
    """进行中条目与事件的匹配档：叶子优先于根，对不上为 0。"""
    if leaf and _ids_equal(leaf, item.get("leafEventId")):
        return 3
    if root and _ids_equal(root, item.get("rootEventId")):
        return 2
    raw = item.get("eventId") or item.get("event_id")
    if leaf and _ids_equal(leaf, raw):
        return 1
    if root and _ids_equal(root, raw):
        return 1
    return 0


def match_active_item(
    event_id: str,
    eta_items: List[Dict[str, Any]],
    full_events: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """按叶子、根的优先级取进行中 ETA 的整条，供读取预计用量或时长。"""
    if not eta_items:
        return None
    leaf, root = _event_match_ids(event_id, full_events)
    if not leaf and not root:
        return None
    best: Optional[Dict[str, Any]] = None
    best_rank = 0
    for it in eta_items:
        if not isinstance(it, dict):
            continue
        rank = _active_id_rank(it, leaf, root)
        if rank > best_rank:
            best = it
            best_rank = rank
    return best


def _pick_imminent_among(
    matched: List[Dict[str, Any]],
    *,
    now: Optional[datetime] = None,
) -> Optional[Dict[str, Any]]:
    """多条 pending：最近的未来 nextAt，否则最近的过去；无 nextAt 取第一条。"""
    if not matched:
        return None
    timed: List[Tuple[int, Dict[str, Any]]] = []
    for it in matched:
        nxt = _parse_unix_sec(it.get("nextAt") or it.get("next_at"))
        if nxt is not None:
            timed.append((nxt, it))
    if not timed:
        return matched[0]
    tz = shanghai_tz()
    current = now or datetime.now(tz=tz)
    if current.tzinfo is None:
        current = current.replace(tzinfo=tz)
    else:
        current = current.astimezone(tz)
    now_ts = int(current.timestamp())
    future = sorted((n, it) for n, it in timed if n >= now_ts)
    if future:
        return future[0][1]
    return max(timed, key=lambda pair: pair[0])[1]


def match_imminent_item(
    event_id: str,
    events: List[Dict[str, Any]],
    full_events: List[Dict[str, Any]],
    *,
    now: Optional[datetime] = None,
) -> Optional[Dict[str, Any]]:
    """
    取 imminent 整条：先 eventId（叶/根），未命中且所指为根时再按 parentEventName。

    业务说明：
    非合并子 pending 的 eventId 是子；用户说根名时 eventId 对不上，
    用目录根权威 name 对齐 parentEventName（仅根话语启用，避免叶子 miss 误命中兄弟）。
    多条时与 nextAt 选择相同。忽略 expectLeafTitle。
    """
    if not events:
        return None
    leaf, root = _event_match_ids(event_id, full_events)
    if not leaf and not root:
        return None
    matched: List[Dict[str, Any]] = []
    for it in events:
        if not isinstance(it, dict):
            continue
        eid = it.get("eventId") or it.get("event_id")
        if (leaf and _ids_equal(leaf, eid)) or (root and _ids_equal(root, eid)):
            matched.append(it)
    hit = _pick_imminent_among(matched, now=now)
    if hit is not None:
        return hit

    # 仅当话语指向根（leaf==root）时用 parentEventName 反推
    if not root or (leaf and leaf != root):
        return None
    root_name = catalog_event_name(root, full_events)
    if not root_name:
        return None
    by_parent: List[Dict[str, Any]] = []
    for it in events:
        if not isinstance(it, dict):
            continue
        if read_parent_event_name(it) == root_name:
            by_parent.append(it)
    return _pick_imminent_among(by_parent, now=now)


def format_go_measure_answer(
    *,
    event_name: str,
    aspect: str,
    duration_sec: Optional[int] = None,
    amount: Optional[float] = None,
    unit: str = "",
) -> str:
    """用 Go 给出的预计时长或用量说一句。没有该格时返回空串。"""
    name = (event_name or "").strip() or "这件事"
    if aspect == "duration" and duration_sec and duration_sec > 0:
        return f"这次{name}预计持续大约{_format_remain_hm(int(duration_sec))}。"
    if aspect == "amount" and amount and amount > 0:
        num = float(amount)
        text = str(int(num)) if num.is_integer() else str(num)
        return f"这次{name}预计大约{text}{(unit or '').strip()}。"
    return ""


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
    item = match_imminent_item(
        event_id, events, full_events, now=now
    )
    if not item:
        return None
    return _parse_unix_sec(item.get("nextAt") or item.get("next_at"))


def format_active_in_progress_answer(event_name: str = "") -> str:
    """
    active 命中但无正 expectEndAt 时的降级话术。

    MUST NOT 编造预计结束钟点；只表达进行中。
    """
    name = (event_name or "").strip() or "这件事"
    return f"「{name}」现在正在进行中，暂时还没有预计结束时间。"


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
