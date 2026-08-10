"""
护理留意分析提示词

业务说明：
系统侧静态块来自本地挂载卷 prompt.json（含输出格式与可选对比样例）；
用户侧运行时注入宝宝月龄、近两日紧凑史与事件 id 对照表。
有近两日史且对照表可用时至少一条留意；必须结合月龄；无通识知识摘录。
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
    组装用户消息：日键、月龄、画像、今昨紧凑史、名 id 对照。

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
        history_events, now=now
    )

    sex_raw = baby_profile.get("sex")
    if sex_raw == 0:
        sex_line = "宝宝性别：女"
    elif sex_raw == 1:
        sex_line = "宝宝性别：男"
    else:
        sex_line = "宝宝性别：未知"

    age_hint = (
        f"你是一位专业的育儿专家，请结合宝宝月龄（{baby_age_months} 个月）选择留意点与措辞；"
        if isinstance(baby_age_months, int)
        else "宝宝月龄未知：不要编造具体月龄或月龄常模数字；"
    )

    parts = [
        _format_age(baby_age_months),
        sex_line,
        f"逻辑日：{day or '（未指定）'}",
        (
            f"{age_hint}"
            "请结合「近两日记录」判断今天值得留意的点，如涉及建议则必须阐明不作为医疗诊断。"
            "当近两日记录非空且下方「事件名与 id」对照表可用时：items 必须至少 1 条；"
            "弱信号也可用温和语气、偏低 score 轻提，禁止因此返回空列表。"
            "仅当记录为空或无法回填 eventId 时，items 才可为 []。"
            "不要编造通识/知识库依据。"
            "若系统侧有「用户反馈对比样例」，按样例调节宜提/轻提，勿当作本宝宝记录，"
            "有近两日记录时不要理解成全部不提。"
            "eventId 必须来自对照表。严格按系统要求输出 JSON。"
        ),
        f"近两日记录（今天/昨天；相对次数/时间；无 id）：\n{history_text}",
    ]
    if legend:
        parts.append(
            f"事件名与 id（仅回填 eventId 用，勿写入流水）：\n{legend}"
        )
    else:
        parts.append(
            "事件名与 id：（无）无法可靠回填 eventId，此时允许 items 为空，禁止臆造 id。"
        )

    if history_summary not in (None, {}, [], ""):
        try:
            hs = json.dumps(history_summary, ensure_ascii=False, default=str)
        except TypeError:
            hs = str(history_summary)
        if hs and hs not in ("{}", "[]", "null"):
            parts.append(f"编排侧历史摘要（参考，非通识库）：\n{hs}")

    return "\n\n".join(parts)
