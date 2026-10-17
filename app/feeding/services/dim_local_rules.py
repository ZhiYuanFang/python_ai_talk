"""
各维本地规则（飞轮之前）

业务说明：
只接整句框架清楚的说法。不中则返回空，交给飞轮和小模型。
「吃了多少」是查记录，「这次要吃多少」是预测用量。
"""

from __future__ import annotations

import re
from typing import Optional, Tuple

from app.feeding.services.rule_gap_store import rule_gap_store
from app.shared.constants import IntentOp, TargetType

# 预测用量：要吃/要喝多少，且不是「吃了多少」
_PREDICT_AMOUNT_RE = re.compile(
    r"这次要吃多少|这次要喝多少|要吃多少|要喝多少|大概要吃多少|大概要喝多少|大概还要吃多少"
)
_RECORD_AMOUNT_RE = re.compile(r"吃了多少|喝了多少|拉了多少|尿了多少")
_PREDICT_DURATION_RE = re.compile(r"这次要吃多久|这次要喝多久|这次要睡多久|要吃多久|要喝多久")
_RECORD_DURATION_RE = re.compile(r"睡了多久|吃了多久|喝了多久|拉了多久")
_PREDICT_WHEN_RE = re.compile(r"还要多久|还要多长时间|还有多久|几点吃|什么时候吃|什么时候喝")
_RECORD_POINT_RE = re.compile(r"上次|上一次|最近一次|几次|多少次")
_CREATE_RE = re.compile(r"吃了|喝了|拉了|尿了|睡了|开始")
_QUESTION_RE = re.compile(r"多少|多久|几次|什么时候|还要")

_LOCATE_OPEN_RE = re.compile(r"正在进行|还没结束|进行中的")
_LOCATE_DONE_RE = re.compile(r"已完成的|做完的那次")
_LOCATE_LATEST_RE = re.compile(r"最近一条|上一条|刚才那条")


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
