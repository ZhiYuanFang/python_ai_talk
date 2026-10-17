"""
各维本地规则（飞轮之前）

业务说明：
只接整句框架清楚的说法。不中则返回空，交给飞轮和小模型。
「吃了多少」是查记录，「这次要吃多少」是预测用量。
"""

from __future__ import annotations

import re
from typing import Optional, Tuple

from app.feeding.services.dim_rule_lexicon import (
    CREATE_VERBS,
    LOCATE_DONE_WORDS,
    LOCATE_LATEST_WORDS,
    LOCATE_OPEN_WORDS,
    PREDICT_AMOUNT_WORDS,
    PREDICT_DURATION_WORDS,
    PREDICT_WHEN_WORDS,
    PRIOR_WORDS,
    QUESTION_WORDS,
    RECORD_AMOUNT_WORDS,
    RECORD_DURATION_WORDS,
    RECORD_POINT_EXTRA_WORDS,
    words_pattern,
)
from app.feeding.services.rule_gap_store import rule_gap_store
from app.shared.constants import IntentOp, TargetType

# 正则来自规则名词模块，判断顺序仍是预测用量先于记一笔
_PREDICT_AMOUNT_RE = words_pattern(PREDICT_AMOUNT_WORDS)
_RECORD_AMOUNT_RE = words_pattern(RECORD_AMOUNT_WORDS)
_PREDICT_DURATION_RE = words_pattern(PREDICT_DURATION_WORDS)
_RECORD_DURATION_RE = words_pattern(RECORD_DURATION_WORDS)
_PREDICT_WHEN_RE = words_pattern(PREDICT_WHEN_WORDS)
_RECORD_POINT_RE = words_pattern(PRIOR_WORDS + RECORD_POINT_EXTRA_WORDS)
_CREATE_RE = words_pattern(CREATE_VERBS)
_QUESTION_RE = words_pattern(QUESTION_WORDS)

_LOCATE_OPEN_RE = words_pattern(LOCATE_OPEN_WORDS)
_LOCATE_DONE_RE = words_pattern(LOCATE_DONE_WORDS)
_LOCATE_LATEST_RE = words_pattern(LOCATE_LATEST_WORDS)


def record_rule_miss(
    *,
    dimension: str,
    segment_text: str,
    utterance: str = "",
    via: str,
    llm_result: str = "",
    device_no: str = "",
) -> None:
    """规则未命中后的去向：via 为 flywheel 或 llm。"""
    rule_gap_store.record(
        dimension=dimension,
        segment_text=segment_text,
        utterance=utterance or segment_text,
        reason=f"rule_miss_{via}",
        llm_used=via == "llm",
        llm_result=llm_result,
        device_no=device_no,
    )


def match_local_frame(
    text: str,
) -> Optional[Tuple[str, str, str, str, str, str, bool, list, str]]:
    """
    操作轨与查/预测的本地框架。

    Returns:
        resolve_type 的九元组，或 None。
    """
    raw = text or ""
    if _PREDICT_AMOUNT_RE.search(raw) and not _RECORD_AMOUNT_RE.search(raw):
        return (
            TargetType.READ.value,
            "",
            "",
            "next",
            "",
            "amount",
            False,
            [],
            "predict",
        )
    if _RECORD_AMOUNT_RE.search(raw) or _RECORD_DURATION_RE.search(raw):
        return (
            TargetType.READ.value,
            IntentOp.READ.value,
            "point",
            "",
            "",
            "",
            False,
            [],
            "record",
        )
    if _PREDICT_DURATION_RE.search(raw):
        return (
            TargetType.READ.value,
            "",
            "",
            "next",
            "",
            "duration",
            False,
            [],
            "predict",
        )
    if _PREDICT_WHEN_RE.search(raw):
        return (
            TargetType.READ.value,
            "",
            "",
            "next",
            "remain",
            "when",
            False,
            [],
            "predict",
        )
    if _RECORD_POINT_RE.search(raw):
        mode = "daily" if re.search(r"几次|多少次", raw) else "point"
        return (
            TargetType.READ.value,
            IntentOp.READ.value,
            mode,
            "",
            "",
            "",
            False,
            [],
            "record",
        )
    if _CREATE_RE.search(raw) and not _QUESTION_RE.search(raw):
        return (
            TargetType.CREATE.value,
            IntentOp.CREATE.value,
            "",
            "",
            "",
            "",
            False,
            [],
            "",
        )
    return None


def match_local_locate(text: str) -> Optional[str]:
    """改删定位的稳定说法。不中返回 None。"""
    raw = text or ""
    if _LOCATE_OPEN_RE.search(raw):
        return "open_timer"
    if _LOCATE_DONE_RE.search(raw):
        return "prefer_completed"
    if _LOCATE_LATEST_RE.search(raw):
        return "latest"
    return None
