"""
喂养历史紧凑注入（共享）

业务说明：
将上游已拉取的喂养史按「日历日 × 事件名」聚合成短行，并单独给出 eventName=eventId 对照表；
流水时刻可挂备注；history_text 前缀拼本地「相邻日链式增减」摘要，供多 Agent 共用。
行格式：{日历日}·{eventName}·{HH:MM(备注)/...}·{总量段}；日标签同年 MM-DD、跨年 YYYY-MM-DD。
拉取窗口由调用方决定，本模块不再二次截断。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from app.shared.history_prompt_fields import (
    _parse_epoch,
    _shanghai_tz,
)

# 备注挂时刻时的最大展示字数（超长截断加省略号）
_REMARK_MAX_LEN = 12
# number 类型缺省单位
_DEFAULT_NUMBER_UNIT = "ml"


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
    """取计数单位（eventUnit 等别名）；无则空串。"""
    for key in ("eventUnit", "event_unit", "unit"):
        v = raw.get(key)
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


def _event_remark(raw: Dict[str, Any]) -> str:
    """
    取备注并截断。

    业务逻辑：trim 后空则 ""；超过 _REMARK_MAX_LEN 截断并加省略号。
    """
    remark = raw.get("remark")
    if remark is None:
        return ""
    text = str(remark).strip()
    if not text:
        return ""
    if len(text) <= _REMARK_MAX_LEN:
        return text
    return text[:_REMARK_MAX_LEN] + "…"


def _event_type(raw: Dict[str, Any]) -> str:
    """
    解析事件类型：number|time|one。

    业务逻辑：
    eventNumber > 1  → number
    eventNumber == 0 → time
    eventNumber == 1 → one
    """
    event_number = raw.get("eventNumber", raw.get("event_number"))

    if event_number is None:
        return "one"  # 缺省兜底

    if event_number > 1:
        return "number"
    elif event_number == 0:
        return "time"
    else:
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


def _clock_hm_with_ongoing(raw: Dict[str, Any]) -> Tuple[str, bool]:
    """
    返回 (时钟字符串, 是否进行中)。
    进行中 = 有 start，无 end 或 end <= start
    """
    dt_s = _parse_epoch(raw.get("startTime", raw.get("start_time")))
    dt_e = _parse_epoch(raw.get("endTime", raw.get("end_time")))

    if dt_s is None:
        return "", False

    start_str = f"{dt_s.hour:02d}:{dt_s.minute:02d}"

    # 无 end → 进行中
    if dt_e is None:
        return f"{start_str}~", True

    # end <= start → 异常或没写 end，当进行中处理
    if dt_e <= dt_s:
        return f"{start_str}~", True

    # 跨天：显示范围
    if dt_e.date() != dt_s.date():
        end_str = f"{dt_e.hour:02d}:{dt_e.minute:02d}"
        return f"{start_str}-{end_str}", False

    # 同一天正常事件
    return start_str, False


def _clock_token_with_remark(raw: Dict[str, Any]) -> Tuple[str, bool]:
    """
    时刻 token + 是否进行中；非空备注绑在时刻后。

    业务逻辑：`08:10(AD)`；进行中 `20:56~(夜醒)`（~ 在括号前）。
    """
    clock, ongoing = _clock_hm_with_ongoing(raw)
    if not clock:
        return "", False
    remark = _event_remark(raw)
    if not remark:
        return clock, ongoing
    return f"{clock}({remark})", ongoing


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


def _resolve_number_unit(items: List[Dict[str, Any]]) -> str:
    """组内首个非空 unit；全缺则 ml。"""
    for raw in items:
        u = _event_unit(raw)
        if u:
            return u
    return _DEFAULT_NUMBER_UNIT


def _format_number_sum(items: List[Dict[str, Any]]) -> str:
    """计数总量：总量{sum}{unit}；unit 取组内首个非空，缺省 ml。"""
    total = 0.0
    has_num = False
    for raw in items:
        num = raw.get("eventNumber", raw.get("event_number"))
        if num is None or num == "":
            continue
        try:
            total += float(num)
            has_num = True
        except (TypeError, ValueError):
            continue
    unit = _resolve_number_unit(items)
    if not has_num:
        amount = "0"
    elif total == int(total):
        amount = str(int(total))
    else:
        amount = str(total)
    return f"总量{amount}{unit}"


def _format_amount_number(value: float) -> str:
    """数量展示：整数去小数。"""
    if value == int(value):
        return str(int(value))
    return str(value)


def format_feeding_history_group(
    day_label: str,
    event_name: str,
    items: List[Dict[str, Any]],
) -> str:
    """
    聚合紧凑行：{日历日}·{事件名}·{时刻(备注)/...}·{总量段}

    业务逻辑：
    - 进行中事件时刻后加 ~（如 20:56~）；备注在 ~ 之后括号
    - time 类型：有进行中时总时长后加 +进行中 标注
    - 组内 items 须已按 start 升序
    """
    if not items:
        return ""

    kind = _event_type(items[0])

    # 构建 clocks，同时检测是否有进行中
    clocks: List[str] = []
    has_ongoing = False

    for raw in items:
        hm, ongoing = _clock_token_with_remark(raw)
        if hm:
            clocks.append(hm)
        if ongoing:
            has_ongoing = True

    if not clocks:
        return ""

    clocks_str = "/".join(clocks)

    # 总量段
    if kind == "time":
        secs_sum = 0
        for raw in items:
            secs = _duration_seconds(raw)
            if secs is not None:
                secs_sum += secs

        if secs_sum > 0:
            total_seg = _format_total_duration_xhym(secs_sum)
            if has_ongoing:
                total_seg = f"{total_seg}+进行中"
        else:
            # 所有事件都是进行中或时长为0
            total_seg = "进行中" if has_ongoing else "总时长0m"

    elif kind == "number":
        total_seg = _format_number_sum(items)
    else:
        total_seg = f"{len(items)}次"

    return f"{day_label}·{event_name}·{clocks_str}·{total_seg}"


@dataclass
class _DayNameMetric:
    """单日单事件名计量，供链式对比。"""

    kind: str = "one"
    count: int = 0
    amount: float = 0.0  # number 求和；time 为秒
    unit: str = _DEFAULT_NUMBER_UNIT
    items: List[Dict[str, Any]] = field(default_factory=list)


def _accumulate_day_metrics(
    groups: Dict[Tuple[date, str], List[Dict[str, Any]]],
) -> Dict[Tuple[date, str], _DayNameMetric]:
    """由组字典生成 (日, 名) → 计量。"""
    out: Dict[Tuple[date, str], _DayNameMetric] = {}
    for (d, name), items in groups.items():
        if not items:
            continue
        kind = _event_type(items[0])
        m = _DayNameMetric(kind=kind, count=len(items), items=list(items))
        if kind == "number":
            total = 0.0
            for raw in items:
                num = raw.get("eventNumber", raw.get("event_number"))
                if num is None or num == "":
                    continue
                try:
                    total += float(num)
                except (TypeError, ValueError):
                    continue
            m.amount = total
            m.unit = _resolve_number_unit(items)
        elif kind == "time":
            secs_sum = 0
            for raw in items:
                secs = _duration_seconds(raw)
                if secs is not None:
                    secs_sum += secs
            m.amount = float(secs_sum)
        out[(d, name)] = m
    return out


def _format_delta_clause(
    name: str,
    prev: _DayNameMetric,
    curr: _DayNameMetric,
) -> Optional[str]:
    """
    单事件相邻日增减子句；无法比或 Δ=0 返回 None。

    业务逻辑：两侧须同名已计量；按 kind 比数量/时长/次数。
    """
    # 两侧 kind 不一致时以 curr 为准仍可比次数；计量字段按各自 kind
    if prev.kind == "number" and curr.kind == "number":
        delta = curr.amount - prev.amount
        if delta == 0:
            return None
        unit = curr.unit or prev.unit or _DEFAULT_NUMBER_UNIT
        sign = "+" if delta > 0 else ""
        return f"{name} {sign}{_format_amount_number(delta)}{unit}"
    if prev.kind == "time" and curr.kind == "time":
        delta_min = _seconds_to_rounded_minutes(
            int(curr.amount)
        ) - _seconds_to_rounded_minutes(int(prev.amount))
        if delta_min == 0:
            return None
        sign = "+" if delta_min > 0 else ""
        return f"{name} {sign}{delta_min}分钟"
    # one 或 kind 混用：只比次数
    delta_c = curr.count - prev.count
    if delta_c == 0:
        return None
    sign = "+" if delta_c > 0 else ""
    return f"{name} {sign}{delta_c}次"


def build_day_chain_summary(
    groups: Dict[Tuple[date, str], List[Dict[str, Any]]],
    *,
    anchor: date,
) -> str:
    """
    窗内全部日历日相邻链式增减摘要（无标题）。

    Returns:
        多行文本；无可比 Δ 时返回空串
    """
    metrics = _accumulate_day_metrics(groups)
    if not metrics:
        return ""

    days = sorted({d for (d, _) in metrics.keys()})
    if len(days) < 2:
        return ""

    lines: List[str] = []
    for i in range(1, len(days)):
        prev_d, curr_d = days[i - 1], days[i]
        names = sorted(
            {
                n
                for (d, n) in metrics.keys()
                if d == prev_d or d == curr_d
            }
        )
        clauses: List[str] = []
        for name in names:
            prev_m = metrics.get((prev_d, name))
            curr_m = metrics.get((curr_d, name))
            # 双侧缺一侧：跳过
            if prev_m is None or curr_m is None:
                continue
            clause = _format_delta_clause(name, prev_m, curr_m)
            if clause:
                clauses.append(clause)
        if not clauses:
            continue
        prev_label = _format_day_label(prev_d, anchor)
        curr_label = _format_day_label(curr_d, anchor)
        lines.append(f"{curr_label}较{prev_label}：{'；'.join(clauses)}")
    return "\n".join(lines)


def build_feeding_history_prompt_blocks(
    history_events: List[Dict[str, Any]] | None,
    *,
    now: Optional[datetime] = None,
    day: Optional[str] = None,
) -> Tuple[str, str]:
    """
    构建按日历日×事件名聚合流水与名→id 对照表。

    业务逻辑：
    history_text = 可选【本地摘要】日链式增减 + 空行 + 流水行（时刻可带备注）。

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
            line = format_feeding_history_group(day_label, name, items)
            if line:
                lines.append(line)

    flow_text = "\n".join(lines) if lines else "（无）"
    summary_body = build_day_chain_summary(groups, anchor=anchor)
    if summary_body:
        history_text = f"【本地摘要】\n{summary_body}\n\n{flow_text}"
    else:
        history_text = flow_text

    if not name_to_id:
        legend = ""
    else:
        legend_lines = [
            f"{n}={i}" for n, i in sorted(name_to_id.items(), key=lambda x: x[0])
        ]
        legend = "\n".join(legend_lines)
    return history_text, legend
