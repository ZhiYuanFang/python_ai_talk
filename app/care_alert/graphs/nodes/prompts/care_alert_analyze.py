"""
护理留意分析提示词

业务说明：
系统侧静态块来自本地挂载卷 prompt.json（判定规则 + JSON 格式 + 可选对比样例）；
用户侧仅运行时注入月龄、性别、逻辑日、近期按日聚合史与事件 id 对照表，不复述政策。
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.care_alert.graphs.nodes.prompts.history_compact import (
    build_care_alert_history_prompt_blocks,
)
from app.care_alert.services.prompt_store import (
    build_system_prompt_from_doc,
    load_or_bootstrap_prompt,
)
from app.tip.graphs.nodes.derive_baby_age import shanghai_now


def build_care_alert_system_prompt() -> str:
    """
    系统提示词：从本地 prompt 文档加载（缺失则 bootstrap / 版本迁移）。

    Returns:
        系统提示词字符串（输出格式 + 可选对比样例）
    """
    doc = load_or_bootstrap_prompt()
    return build_system_prompt_from_doc(doc)


def _format_age(baby_age_months: Optional[int]) -> str:
    """月龄提示词行（仅运行时，不落盘）。"""
    if baby_age_months is None:
        return "宝宝月龄：未知"
    return f"宝宝月龄：{baby_age_months} 个月"


def build_care_alert_user_message(
    *,
    day: str,
    baby_age_months: Optional[int],
    history_events: List[Dict[str, Any]],
    baby_profile: Dict[str, Any],
    history_summary: Any = None,
) -> str:
    """
    组装用户消息：仅实例数据（月龄/性别/逻辑日/史/对照表），政策见 system。

    Args:
        day: 上海逻辑日
        baby_age_months: 月龄或 None
        history_events: 原始历史列表
        baby_profile: 宝宝画像
        history_summary: Go 可选透传历史摘要

    Returns:
        用户消息字符串（动态，不写入 prompt.json）
    """
    now = shanghai_now()
    history_text, legend = build_care_alert_history_prompt_blocks(
        history_events, now=now, day=day
    )

    sex_raw = baby_profile.get("sex")
    if sex_raw == 0:
        sex_line = "宝宝性别：女"
    elif sex_raw == 1:
        sex_line = "宝宝性别：男"
    else:
        sex_line = "宝宝性别：未知"

    parts = [
        _format_age(baby_age_months),
        sex_line,
        f"逻辑日：{day or '（未指定）'}",
        "请按系统侧判定依据与 JSON 输出格式作答。",
        f"近期记录（按日聚合：日期·时刻与总量；无 id）：\n{history_text}",
    ]
    if legend:
        parts.append(
            f"事件名与 id（仅回填 eventId 用，勿写入流水）：\n{legend}"
        )
    else:
        parts.append("事件名与 id：（无）")

    if history_summary not in (None, {}, [], ""):
        try:
            hs = json.dumps(history_summary, ensure_ascii=False, default=str)
        except TypeError:
            hs = str(history_summary)
        if hs and hs not in ("{}", "[]", "null"):
            parts.append(f"编排侧历史摘要（参考，非通识库）：\n{hs}")

    return "\n\n".join(parts)
