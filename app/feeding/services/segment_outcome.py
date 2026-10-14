"""
段级 CRUD 结果与整轮汇总

业务说明：
复合句逐段执行后，用统一话术拼接各段成功/追问/暂不支持/失败。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class SegmentOutcome:
    """单段执行结果。"""

    segment_text: str
    rail: str = ""
    # ok | clarify | other | error | exit
    status: str = "ok"
    message: str = ""
    # 可选：供后续确认管线使用
    need_clarify: bool = False


def summarize_segment_outcomes(outcomes: List[SegmentOutcome]) -> str:
    """
    整轮汇总话术。

    例：换尿布已记录。吃奶需要补充毫升数。宝宝今天正常吗暂不支持。
    """
    if not outcomes:
        return ""
    parts: List[str] = []
    for o in outcomes:
        msg = (o.message or "").strip().rstrip("。")
        if not msg:
            continue
        parts.append(msg)
    if not parts:
        return ""
    return "。".join(parts) + "。"


OTHER_UNSUPPORTED_MSG = "，你可以再说喂养记录或查询相关的内容"
