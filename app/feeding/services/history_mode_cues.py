"""
查史 point/daily 原文强线索

业务说明：
供意图缓存命中门闩与分类启发共用词表，避免几次↔上一次串台。
仅当能推断期望 mode 时才用于拒命中；模糊原文不拦。
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from app.feeding.services.intent_events import event_ops, has_read_events
from app.shared.constants import IntentOp, TargetType

# 与 classify_intent 区段启发对齐
DAILY_HINT_RE = re.compile(
    r"几次|多少次|一共|总共|吃了什么|喝了多少|和昨天比|比昨天"
)

# 次数问（比 daily 更窄）：用于播报显式 N 次，不含「吃了什么」
COUNT_HINT_RE = re.compile(r"几次|多少次")

_POINT_CUES = ("上一次", "上次", "最近一次")


def infer_expected_history_mode(text: str) -> Optional[str]:
    """
    从用户原文推断期望的 history_mode。

    Returns:
        "daily" | "point" | None（无线索则不推断）
    """
    raw = text or ""
    # 次数/合计类优先 daily（避免与「什么时候」并存时误判）
    if DAILY_HINT_RE.search(raw):
        return "daily"
    if any(k in raw for k in _POINT_CUES):
        return "point"
    # 点查语气：问「什么时候」且无汇总词
    if "什么时候" in raw:
        return "point"
    return None


def is_count_query(text: str) -> bool:
    """是否为次数问（几次/多少次），供 daily 播报突出次数。"""
    return bool(COUNT_HINT_RE.search(text or ""))


def day_phrase_for_speak(text: str) -> str:
    """次数播报用的日口语前缀。"""
    raw = text or ""
    if "前天" in raw:
        return "前天"
    if re.search(r"昨天|昨日", raw):
        return "昨天"
    if re.search(r"今天|今日", raw):
        return "今天"
    if re.search(r"本周|这周", raw):
        return "本周"
    return "这段时间"


def payload_history_mode(payload: Dict[str, Any]) -> str:
    """载荷 mode；缺省或非法视为 point（与 speak 回落一致）。"""
    hm = str(payload.get("history_mode") or "").strip().lower()
    return hm if hm in ("point", "daily") else "point"


def is_history_read_payload(payload: Dict[str, Any]) -> bool:
    """是否为查史 read 载荷（含 target=history）。"""
    if has_read_events(payload):
        return True
    if str(payload.get("target_type") or "").strip().lower() == TargetType.HISTORY.value:
        return True
    return IntentOp.READ.value in event_ops(payload)


def history_mode_cache_conflict(text: str, payload: Dict[str, Any]) -> bool:
    """
    缓存门闩：原文强线索与载荷 history_mode 冲突则为 True（应拒命中）。

    业务逻辑：无线索或一致 → False；仅冲突 → True。
    """
    if not is_history_read_payload(payload):
        return False
    expected = infer_expected_history_mode(text)
    if not expected:
        return False
    actual = payload_history_mode(payload)
    return expected != actual
