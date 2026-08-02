"""readable history times + latest window + summary detection."""

from datetime import datetime, timedelta, timezone

from app.feeding.utils.query_utterance import looks_like_history_query
from app.shared.history_prompt_fields import (
    build_daily_history_summary,
    format_history_time,
    looks_like_summary_query,
    slim_history_events_for_prompt,
)

# 与生产一致：无 tzdata 时用固定 UTC+8
_TZ = timezone(timedelta(hours=8))
_NOW = datetime(2026, 8, 2, 11, 0, 0, tzinfo=_TZ)


def test_format_relative_minutes_and_today():
    # 30 minutes ago
    ts = _NOW.timestamp() - 30 * 60
    assert format_history_time(ts, now=_NOW, style="relative") == "30分钟前"
    # earlier today
    today = datetime(2026, 8, 2, 8, 30, 0, tzinfo=_TZ).timestamp()
    assert format_history_time(today, now=_NOW, style="relative") == "今天 08:30"


def test_format_ms_and_calendar():
    dt = datetime(2026, 7, 28, 15, 5, 0, tzinfo=_TZ)
    ms = int(dt.timestamp() * 1000)
    assert format_history_time(ms, now=_NOW, style="calendar") == "7月28日 15:05"


def test_slim_takes_newest_not_oldest():
    events = [
        {"eventName": "旧", "startTime": _NOW.timestamp() - 86400 * 3},
        {"eventName": "新", "startTime": _NOW.timestamp() - 60},
        {"eventName": "中", "startTime": _NOW.timestamp() - 3600},
    ]
    slim = slim_history_events_for_prompt(events, limit=2, time_style="relative", now=_NOW)
    assert [e["eventName"] for e in slim] == ["新", "中"]
    assert "分钟前" in slim[0]["startTime"]


def test_summary_and_history_query_gate():
    q = "总结最近7天孩子的吃奶变化"
    assert looks_like_summary_query(q)
    assert looks_like_history_query(q)


def test_daily_summary_has_counts():
    day1 = datetime(2026, 8, 1, 10, 0, 0, tzinfo=_TZ).timestamp()
    day2 = datetime(2026, 8, 1, 14, 0, 0, tzinfo=_TZ).timestamp()
    text = build_daily_history_summary(
        [
            {"eventName": "配方奶", "startTime": day1, "eventNumber": 120},
            {"eventName": "配方奶", "startTime": day2, "eventNumber": 80},
        ],
        now=_NOW,
    )
    assert "按日汇总" in text
    assert "配方奶2次共200" in text
