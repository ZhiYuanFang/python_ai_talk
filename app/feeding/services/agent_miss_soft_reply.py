"""
覆盖缺口对外回答（非 AIGC）

业务说明：
miss 已用硬文案落库（inbox / fail_kind）。对外不再调用 LLM，
固定回复「我只能回答信息记录相关问题」，避免意图出口带 AIGC 属性。
不影响 fail_kind 与统计（仍以硬文案归类）。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

# miss 对外固定话术：非生成式，合规口径下不申报 AIGC
MISS_FIXED_OUTWARD_REPLY = "我只能回答信息记录相关问题"


def fixed_miss_outward_reply() -> str:
    """返回 miss 对外固定句。"""
    return MISS_FIXED_OUTWARD_REPLY


async def soft_reply_for_miss(
    *,
    utterance: str = "",
    hard_content: str = "",
    fail_kind: str = "",
    device_no: str = "",
    llm_model: Optional[Dict[str, Any]] = None,
) -> str:
    """
    兼容旧调用名：不再 LLM，直接返回固定话术。

    参数保留供路由签名兼容；一律忽略。有硬文案（已落库）时才替换对外句。
    """
    del utterance, fail_kind, device_no, llm_model
    if not (hard_content or "").strip():
        return hard_content or ""
    return MISS_FIXED_OUTWARD_REPLY
