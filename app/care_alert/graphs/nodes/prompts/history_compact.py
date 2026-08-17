"""
护理留意历史紧凑注入

业务说明：
将上游已拉取的喂养史按「日历日 × 事件名」聚合成短行，并单独给出 eventName=eventId 对照表，
避免 JSON 全量与史行内重复 id，缩短 care_alert 提示词。
行格式：{日历日}·{eventName}·{HH:MM/...}·{总量段}；日标签同年 MM-DD、跨年 YYYY-MM-DD。
拉取窗口由调用方决定，本模块不再二次截断今昨。
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from app.shared.history_prompt_fields import (
    _parse_epoch,
    _shanghai_tz,
)


def _event_id(raw: Dict[str, Any]) -> str:
    """取事件 id（多种别名）。"""
    for key in ("eventId", "event_id", "id"):
        v = raw.get(key)
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


def _event_name(raw: Dict[str, Any]) -> str:
    """取事件中文名。"""
    name = raw.get("eventName") or raw.get("event_name") or ""
    return str(name).strip() or "未知"


def _event_unit(raw: Dict[str, Any]) -> str:
    """取计数单位（eventUnit 等别名）。"""
    for key in ("eventUnit", "event_unit", "unit"):
        v = raw.get(key)
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


def _event_type(raw: Dict[str, Any]) -> str:
    """
    解析事件类型：number|time|one。

    业务逻辑：
    优先 eventType；缺省时：有起止且时长>=1 秒 → time；
    有 eventNumber → number；否则 one。
    """
    t = raw.get("eventType") or raw.get("event_type") or ""
    t = str(t).strip().lower()
    if t in ("number", "time", "one"):
        return t

    start = raw.get("startTime", raw.get("start_time"))
    end = raw.get("endTime", raw.get("end_time"))
    dt_s = _parse_epoch(start)
    dt_e = _parse_epoch(end)
    if dt_s is not None and dt_e is not None:
        secs = int((dt_e - dt_s).total_seconds())
        if secs >= 1:
            return "time"

    num = raw.get("eventNumber", raw.get("event_number"))
    if num is not None and num != "":
        try:
            float(num)
            return "number"
        except (TypeError, ValueError):
            pass
    return "one"


def _duration_seconds(raw: Dict[str, Any]) -> Optional[int]:
    """计时事件：end-start 秒数；无效则 None。"""
    dt_s = _parse_epoch(raw.get("startTime", raw.get("start_time")))
    dt_e = _parse_epoch(raw.get("endTime", raw.get("end_time")))
    if dt_s is None or dt_e is None:
        return None
    secs = int((dt_e - dt_s).total_seconds())
    if secs < 0:
        return None
    return secs


def _event_date(raw: Dict[str, Any]) -> Optional[date]:
    """取事件所属上海日历日（start 优先，否则 end）。"""
    dt = _parse_epoch(raw.get("startTime", raw.get("start_time")))
    if dt is None:
        dt = _parse_epoch(raw.get("endTime", raw.get("end_time")))
    if dt is None:
        return None
    return dt.date()


def _sort_epoch(raw: Dict[str, Any]) -> float:
    """排序键：start 优先，否则 end。"""
    for candidate in (
        raw.get("startTime", raw.get("start_time")),
        raw.get("endTime", raw.get("end_time")),
    ):
        dt = _parse_epoch(candidate)
        if dt is not None:
            return dt.timestamp()
    return 0.0


def _parse_anchor_date(
    day: Optional[str],
    *,
    now: datetime,
) -> date:
    """
    解析逻辑日锚点。

    业务逻辑：优先 YYYY-MM-DD；无效则回退 now 的上海日历日。
    """
    if day and str(day).strip():
        text = str(day).strip()[:10]
        try:
            return date.fromisoformat(text)
        except ValueError:
            pass
    return now.date()


def _format_day_label(event_day: date, anchor: date) -> str:
    """
    日历日标签：与锚点同年 → MM-DD；跨年 → YYYY-MM-DD。
    """
    if event_day.year == anchor.year:
        return f"{event_day.month:02d}-{event_day.day:02d}"
    return event_day.isoformat()


def _clock_hm(raw: Dict[str, Any]) -> Optional[str]:
    """单次 start 的 HH:MM；无 start 则用 end。"""
    dt = _parse_epoch(raw.get("startTime", raw.get("start_time")))
    if dt is None:
        dt = _parse_epoch(raw.get("endTime", raw.get("end_time")))
    if dt is None:
        return None
    return f"{dt.hour:02d}:{dt.minute:02d}"


def _seconds_to_rounded_minutes(secs: int) -> int:
    """总秒 → 总分钟，非负四舍五入。"""
    if secs <= 0:
        return 0
    return (secs + 30) // 60


def _format_total_duration_xhym(total_seconds: int) -> str:
    """
    计时总量文案：总时长XhYm。

    业务逻辑：小时为 0 时省略 0h；全无有效时长则为 总时长0m。
    """
    mins = _seconds_to_rounded_minutes(max(0, total_seconds))
    hours, rem = divmod(mins, 60)
    if hours > 0:
        return f"总时长{hours}h{rem}m"
    return f"总时长{rem}m"


def _format_number_sum(items: List[Dict[str, Any]]) -> str:
    """计数总量：总量{sum}{unit}；unit 取组内首个非空。"""
    total = 0.0
    has_num = False
    unit = ""
    for raw in items:
        if not unit:
            unit = _event_unit(raw)
        num = raw.get("eventNumber", raw.get("event_number"))
        if num is None or num == "":
            continue
        try:
            total += float(num)
            has_num = True
        except (TypeError, ValueError):
            continue
    if not has_num:
        amount = "0"
    elif total == int(total):
        amount = str(int(total))
    else:
        amount = str(total)
    return f"总量{amount}{unit}"


def format_care_alert_history_group(
    day_label: str,
    event_name: str,
    items: List[Dict[str, Any]],
) -> str:
    """
    聚合紧凑行：{日历日}·{某事}·{HH:MM/...}·{总量段}，不含 eventId。

    业务逻辑：
    - 组内 items 须已按 start 升序
    - 类型取组内第一条；time/number/one 分型写总量

    Returns:
        非空行；无法格式化时返回空串
    """
    if not items:
        return ""
    clocks: List[str] = []
    for raw in items:
        hm = _clock_hm(raw)
        if hm:
            clocks.append(hm)
    if not clocks:
        return ""

    kind = _event_type(items[0])
    if kind == "time":
        secs_sum = 0
        for raw in items:
            secs = _duration_seconds(raw)
            if secs is not None:
                secs_sum += secs
        total_seg = _format_total_duration_xhym(secs_sum)
    elif kind == "number":
        total_seg = _format_number_sum(items)
    else:
        total_seg = f"{len(items)}次"

    return f"{day_label}·{event_name}·{'/'.join(clocks)}·{total_seg}"


def build_care_alert_history_prompt_blocks(
    history_events: List[Dict[str, Any]] | None,
    *,
    now: Optional[datetime] = None,
    day: Optional[str] = None,
) -> Tuple[str, str]:
    """
    构建按日历日×事件名聚合流水与名→id 对照表。

    Args:
        history_events: 上游已拉取的历史（本函数不再按今昨截断）
        now: 上海「现在」，缺省取当前
        day: 逻辑日 YYYY-MM-DD，用作日标签跨年锚点；缺省用 now.date()

    Returns:
        (history_lines_text, name_id_legend_text)；无数据时分别为「（无）」与空串
    """
    now = now or datetime.now(tz=_shanghai_tz())
    anchor = _parse_anchor_date(day, now=now)
    if not history_events:
        return "（无）", ""

    # 仅要求能解析日历日；窗口由拉取侧负责
    dated: List[Dict[str, Any]] = []
    for raw in history_events:
        if not isinstance(raw, dict):
            continue
        if _event_date(raw) is None:
            continue
        dated.append(raw)

    if not dated:
        return "（无）", ""

    by_recency = sorted(dated, key=_sort_epoch, reverse=True)
    name_to_id: Dict[str, str] = {}
    for raw in by_recency:
        name = _event_name(raw)
        eid = _event_id(raw)
        if name and eid and name not in name_to_id:
            name_to_id[name] = eid

    # (日历日, name) → 事件列表
    groups: Dict[Tuple[date, str], List[Dict[str, Any]]] = {}
    for raw in dated:
        d = _event_date(raw)
        if d is None:
            continue
        name = _event_name(raw)
        groups.setdefault((d, name), []).append(raw)

    for key in groups:
        groups[key].sort(key=_sort_epoch)

    # 日期新→旧，同日按事件名
    day_keys = sorted({d for (d, _) in groups.keys()}, reverse=True)
    lines: List[str] = []
    for d in day_keys:
        day_label = _format_day_label(d, anchor)
        names = sorted(n for (gd, n) in groups.keys() if gd == d)
        for name in names:
            items = groups[(d, name)]
            line = format_care_alert_history_group(day_label, name, items)
            if line:
                lines.append(line)

    history_text = "\n".join(lines) if lines else "（无）"
    if not name_to_id:
        legend = ""
    else:
        legend_lines = [f"{n}={i}" for n, i in sorted(name_to_id.items(), key=lambda x: x[0])]
        legend = "\n".join(legend_lines)
    return history_text, legend
