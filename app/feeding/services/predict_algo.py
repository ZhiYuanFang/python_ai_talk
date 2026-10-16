"""
本地预测算法（对齐 Flutter event_next_predictor 场景核）

业务说明：
非预约：近 7 日发生时刻 → TOD 桶 + 半衰期加权中位间隔 → nextAt；
并可估计 expect 时长/用量。预约由调用方旁路，本模块不算间隔。
样本不足返回 status=insufficient_samples，禁止上层用 LLM 编造数字。
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.shared.history_window import shanghai_tz

# 与 Flutter 常量对齐
K_MIN_INTERVAL_SEC = 15 * 60
K_MIN_SAMPLES = 2
K_PREDICTION_RANGE_DAY_SPAN = 7
K_EXPECT_DURATION = "duration"
K_EXPECT_AMOUNT = "amount"


@dataclass
class PredictToolResult:
    """单事件工具输出（可进 Redis 快照 / LLM JSON）。"""

    event_id: str
    event_name: str = ""
    status: str = "ok"  # ok | insufficient_samples | no_appointment | error
    last_at: Optional[int] = None
    next_at: Optional[int] = None
    interval_sec: Optional[int] = None
    confidence: float = 0.0
    expect_kind: Optional[str] = None
    expect_duration_sec: Optional[int] = None
    expect_amount: Optional[float] = None
    expect_unit: Optional[str] = None
    expect_leaf_title: Optional[str] = None
    source: str = "interval"  # interval | appointment | cache
    message: str = ""

    def to_prompt_dict(self) -> Dict[str, Any]:
        """供 LLM 注入的精简字典。"""
        d = asdict(self)
        # 去掉空值，省 token
        return {k: v for k, v in d.items() if v is not None and v != ""}


def prediction_seven_day_unix_bounds(
    now: Optional[datetime] = None,
) -> Tuple[int, int]:
    """
    近 7 个自然日窗：本地 today-6d 00:00 → now（对齐 Flutter）。

    Returns:
        (start_unix, end_unix)
    """
    tz = shanghai_tz()
    n = now or datetime.now(tz=tz)
    if n.tzinfo is None:
        n = n.replace(tzinfo=tz)
    else:
        n = n.astimezone(tz)
    start_day = datetime(n.year, n.month, n.day, tzinfo=tz) - timedelta(days=6)
    return int(start_day.timestamp()), int(n.timestamp())


def half_life_days_for_age_months(months: Optional[int]) -> int:
    """按月龄分段半衰期（天）；未知月龄默认 14。"""
    if months is None:
        return 14
    if months < 2:
        return 7
    if months < 4:
        return 10
    if months < 6:
        return 14
    if months < 12:
        return 21
    return 30


def time_of_day_bucket(ts: datetime) -> int:
    """TOD 桶 0..5。"""
    h = ts.hour
    if h < 6:
        return 0
    if h < 9:
        return 1
    if h < 12:
        return 2
    if h < 15:
        return 3
    if h < 18:
        return 4
    return 5


def _buckets_adjacent(a: int, b: int) -> bool:
    if a == b:
        return True
    return abs(a - b) == 1 or (a == 0 and b == 5) or (a == 5 and b == 0)


def _bucket_weight(sample_bucket: int, anchor_bucket: int) -> float:
    if sample_bucket == anchor_bucket:
        return 1.0
    if _buckets_adjacent(sample_bucket, anchor_bucket):
        return 0.6
    return 0.2


def _recency_weight(age_days: float, half_life_days: int) -> float:
    if half_life_days <= 0:
        return 1.0
    return math.exp(-math.log(2) * age_days / half_life_days)


def _parse_instant(raw: Any, tz) -> Optional[datetime]:
    """解析史行时刻：unix 秒 / 毫秒 / ISO。"""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        v = float(raw)
        if v > 1e12:
            v = v / 1000.0
        if v <= 0:
            return None
        return datetime.fromtimestamp(v, tz=tz)
    s = str(raw).strip()
    if not s:
        return None
    if s.isdigit():
        return _parse_instant(int(s), tz)
    try:
        # 兼容 Z
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=tz)
        return dt.astimezone(tz)
    except Exception:
        return None


def _row_payload(row: Dict[str, Any]) -> Dict[str, Any]:
    """历史行字段可能在顶层或 rawPayload。"""
    p = row.get("rawPayload") or row.get("raw_payload")
    if isinstance(p, dict):
        merged = dict(p)
        for k, v in row.items():
            if k not in merged:
                merged[k] = v
        return merged
    return row


def _event_number(payload: Dict[str, Any]) -> Optional[int]:
    for key in ("eventNumber", "event_number"):
        if key in payload and payload[key] is not None:
            try:
                return int(payload[key])
            except (TypeError, ValueError):
                return None
    return None


def _is_active_timing(row: Dict[str, Any], payload: Dict[str, Any]) -> bool:
    """进行中计时：eventNumber==0 且无有效 end。"""
    n = _event_number(payload)
    if n != 0:
        return False
    tz = shanghai_tz()
    end = _parse_instant(payload.get("endTime") or payload.get("end_time"), tz)
    return end is None


def occurrence_instant(
    row: Dict[str, Any],
    *,
    include_active: bool = False,
) -> Optional[datetime]:
    """
    单次发生时刻（对齐 Flutter occurrenceInstant）。

    计时结束用 end；进行中可选 start；其它用 start/createdAt。
    """
    payload = _row_payload(row)
    tz = shanghai_tz()
    if _is_active_timing(row, payload):
        if not include_active:
            return None
        start = _parse_instant(
            payload.get("startTime") or payload.get("start_time"), tz
        )
        if start:
            return start
        return _parse_instant(
            row.get("createdAt") or row.get("created_at") or row.get("createTime"),
            tz,
        )
    n = _event_number(payload)
    if n == 0:
        return _parse_instant(payload.get("endTime") or payload.get("end_time"), tz)
    start = _parse_instant(
        payload.get("startTime") or payload.get("start_time"), tz
    )
    if start:
        return start
    return _parse_instant(
        row.get("createdAt") or row.get("created_at") or row.get("createTime"),
        tz,
    )


def _history_event_id(row: Dict[str, Any]) -> str:
    for key in ("eventId", "event_id", "leafEventId", "leaf_event_id"):
        v = row.get(key)
        if v is not None and str(v).strip():
            return str(v).strip()
    payload = _row_payload(row)
    for key in ("eventId", "event_id"):
        v = payload.get(key)
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


def _weighted_median_interval(
    samples: List[Tuple[int, float]],
) -> Optional[int]:
    """samples: (interval_sec, weight)。"""
    if not samples:
        return None
    sorted_s = sorted(samples, key=lambda x: x[0])
    total = sum(w for _, w in sorted_s)
    if total <= 0:
        return sorted_s[len(sorted_s) // 2][0]
    acc = 0.0
    for interval, w in sorted_s:
        acc += w
        if acc >= total / 2:
            return interval
    return sorted_s[-1][0]


def _weighted_median_value(samples: List[Tuple[float, float]]) -> Optional[float]:
    if not samples:
        return None
    sorted_s = sorted(samples, key=lambda x: x[0])
    total = sum(w for _, w in sorted_s)
    if total <= 0:
        return sorted_s[len(sorted_s) // 2][0]
    acc = 0.0
    for value, w in sorted_s:
        acc += w
        if acc >= total / 2:
            return value
    return sorted_s[-1][0]


def _collect_weighted_intervals(
    times: List[datetime],
    *,
    anchor_bucket: int,
    half_life_days: int,
    now: datetime,
    strict_buckets: bool,
) -> List[Tuple[int, float]]:
    out: List[Tuple[int, float]] = []
    for i in range(1, len(times)):
        delta = int((times[i] - times[i - 1]).total_seconds())
        if delta < K_MIN_INTERVAL_SEC:
            continue
        b = time_of_day_bucket(times[i - 1])
        bw = _bucket_weight(b, anchor_bucket) if strict_buckets else 1.0
        age_days = (now - times[i]).total_seconds() / 86400.0
        w = bw * _recency_weight(age_days, half_life_days)
        if w > 0.001:
            out.append((delta, w))
    return out


def _leaf_event_type(
    event_id: str,
    catalog: List[Dict[str, Any]],
) -> str:
    eid = str(event_id or "").strip()
    for e in catalog or []:
        if str(e.get("event_id") or "") == eid:
            return str(e.get("event_type") or e.get("type") or "").strip().lower()
    return ""


def _amount_from_row(payload: Dict[str, Any]) -> Optional[float]:
    for key in ("eventNumber", "event_number", "quantity", "amount"):
        if key in payload and payload[key] is not None:
            try:
                v = float(payload[key])
                if v > 0:
                    return v
            except (TypeError, ValueError):
                continue
    return None


def _unit_from_row(payload: Dict[str, Any], catalog_unit: str = "") -> str:
    for key in ("eventUnit", "event_unit", "unit"):
        u = str(payload.get(key) or "").strip()
        if u:
            return u
    return (catalog_unit or "").strip()


def predict_next_for_records(
    *,
    event_id: str,
    event_name: str,
    records: List[Dict[str, Any]],
    catalog: List[Dict[str, Any]],
    now: Optional[datetime] = None,
    half_life_days: int = 14,
) -> PredictToolResult:
    """
    对某事件（已筛到该 root 下的史）做间隔预测 + expect。

    Returns:
        PredictToolResult；样本不足 status=insufficient_samples
    """
    tz = shanghai_tz()
    current = now or datetime.now(tz=tz)
    if current.tzinfo is None:
        current = current.replace(tzinfo=tz)
    else:
        current = current.astimezone(tz)

    times: List[datetime] = []
    for r in records or []:
        if not isinstance(r, dict):
            continue
        t = occurrence_instant(r, include_active=False)
        if t is not None:
            times.append(t)
    times.sort()
    if len(times) < 2:
        return PredictToolResult(
            event_id=event_id,
            event_name=event_name,
            status="insufficient_samples",
            message="数据量太少，无法预测",
            source="interval",
        )

    last_at = times[-1]
    anchor_bucket = time_of_day_bucket(last_at)
    samples = _collect_weighted_intervals(
        times,
        anchor_bucket=anchor_bucket,
        half_life_days=half_life_days,
        now=current,
        strict_buckets=True,
    )
    if len(samples) < K_MIN_SAMPLES:
        samples = _collect_weighted_intervals(
            times,
            anchor_bucket=anchor_bucket,
            half_life_days=half_life_days,
            now=current,
            strict_buckets=False,
        )
    if len(samples) < K_MIN_SAMPLES:
        return PredictToolResult(
            event_id=event_id,
            event_name=event_name,
            status="insufficient_samples",
            last_at=int(last_at.timestamp()),
            message="数据量太少，无法预测",
            source="interval",
        )

    median = _weighted_median_interval(samples)
    if median is None or median < K_MIN_INTERVAL_SEC:
        return PredictToolResult(
            event_id=event_id,
            event_name=event_name,
            status="insufficient_samples",
            last_at=int(last_at.timestamp()),
            message="数据量太少，无法预测",
            source="interval",
        )

    next_at = last_at + timedelta(seconds=median)
    confidence = min(1.0, len(samples) / 7.0)
    result = PredictToolResult(
        event_id=event_id,
        event_name=event_name,
        status="ok",
        last_at=int(last_at.timestamp()),
        next_at=int(next_at.timestamp()),
        interval_sec=int(median),
        confidence=confidence,
        source="interval",
    )

    # expect：时长 / 用量胜出（简化：有把握则挂上；时长优先若最近一条为 time）
    _attach_expect(
        result,
        records=records or [],
        catalog=catalog or [],
        anchor_at=last_at,
        half_life_days=half_life_days,
        now=current,
    )
    return result


def _attach_expect(
    result: PredictToolResult,
    *,
    records: List[Dict[str, Any]],
    catalog: List[Dict[str, Any]],
    anchor_at: datetime,
    half_life_days: int,
    now: datetime,
) -> None:
    """挂 expect duration/amount；不足门槛则保持空。"""
    tz = shanghai_tz()
    duration_points: List[Tuple[datetime, float]] = []
    amount_points: List[Tuple[datetime, float, str, str]] = []
    for r in records:
        if not isinstance(r, dict):
            continue
        payload = _row_payload(r)
        rid = _history_event_id(r)
        et = _leaf_event_type(rid, catalog)
        if et == "one":
            continue
        if _is_active_timing(r, payload):
            continue
        n = _event_number(payload)
        if n == 0:
            start = _parse_instant(
                payload.get("startTime") or payload.get("start_time"), tz
            )
            end = _parse_instant(
                payload.get("endTime") or payload.get("end_time"), tz
            )
            if start and end and end > start:
                sec = (end - start).total_seconds()
                if sec > 0:
                    duration_points.append((start, sec))
        elif n is not None and n > 0 and et != "time":
            amt = _amount_from_row(payload)
            if amt is None:
                continue
            at = occurrence_instant(r, include_active=False) or anchor_at
            unit = _unit_from_row(payload)
            leaf = str(
                payload.get("eventName")
                or payload.get("event_name")
                or result.event_name
                or ""
            ).strip()
            amount_points.append((at, amt, unit, leaf))

    anchor_bucket = time_of_day_bucket(anchor_at)

    def _metric_median(
        points: List[Tuple[datetime, float]],
    ) -> Optional[float]:
        if len(points) < K_MIN_SAMPLES:
            return None
        for strict in (True, False):
            samples: List[Tuple[float, float]] = []
            for at, value in points:
                b = time_of_day_bucket(at)
                bw = _bucket_weight(b, anchor_bucket) if strict else 1.0
                age = (now - at).total_seconds() / 86400.0
                w = bw * _recency_weight(age, half_life_days)
                if w > 0.001:
                    samples.append((value, w))
            if len(samples) >= K_MIN_SAMPLES:
                return _weighted_median_value(samples)
        return None

    dur = _metric_median(duration_points)
    amt_med = None
    amt_unit = ""
    amt_leaf = ""
    if len(amount_points) >= K_MIN_SAMPLES:
        # 用量：按 value 加权中位，单位取最近一条
        plain = [(at, v) for at, v, _, _ in amount_points]
        amt_med = _metric_median(plain)
        if amt_med is not None:
            amount_points.sort(key=lambda x: x[0])
            _, _, amt_unit, amt_leaf = amount_points[-1]

    # 两个数都留下，由 predict_aspect 决定念哪一个，不再二选一丢掉
    if dur is not None and dur > 0:
        result.expect_duration_sec = int(round(dur))
    if amt_med is not None and amt_med > 0:
        result.expect_amount = float(amt_med)
        result.expect_unit = amt_unit or None
        result.expect_leaf_title = amt_leaf or None
    if result.expect_duration_sec and result.expect_amount:
        result.expect_kind = "both"
    elif result.expect_duration_sec:
        result.expect_kind = K_EXPECT_DURATION
    elif result.expect_amount:
        result.expect_kind = K_EXPECT_AMOUNT


def filter_records_for_root(
    records: List[Dict[str, Any]],
    root_event_id: str,
    catalog: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """筛出归属该根的历史行。"""
    from app.feeding.services.event_hierarchy import get_root_event_id

    root = str(root_event_id or "").strip()
    if not root:
        return []
    out: List[Dict[str, Any]] = []
    for r in records or []:
        if not isinstance(r, dict):
            continue
        eid = _history_event_id(r)
        if not eid:
            continue
        rroot = get_root_event_id(eid, catalog) or eid
        if rroot == root:
            out.append(r)
    return out


def appointment_tool_result(
    *,
    event_id: str,
    event_name: str,
    next_at: int,
) -> PredictToolResult:
    """预约约定 → 工具结果；next_at<=0 为无约定。"""
    if int(next_at or 0) < 1:
        return PredictToolResult(
            event_id=event_id,
            event_name=event_name,
            status="no_appointment",
            message="还没有约定下次时间",
            source="appointment",
        )
    return PredictToolResult(
        event_id=event_id,
        event_name=event_name,
        status="ok",
        next_at=int(next_at),
        confidence=1.0,
        source="appointment",
    )
