"""
护理留意分析提示词

业务说明：
引导 LLM 基于月龄、近期喂养史与「合格」通识知识，判定今天是否值得留意。
准确优先：无合格通识不编造、不硬塞；史信号不足时 items 可为 []。
语气非医疗诊断；每项必须含 followUpPrompt。
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.shared.history_prompt_fields import slim_history_events_for_prompt
from app.tip.graphs.nodes.derive_baby_age import shanghai_now


def build_care_alert_system_prompt() -> str:
    """
    系统提示词：角色、判定规则与硬输出格式。

    Returns:
        系统提示词字符串
    """
    return """
你是一位有经验的母婴闺蜜，帮家长判断今天有没有「值得留意」的护理点。
态度：温和提醒、不是诊断、不开药、不恐吓。可用「值得留意」「可以多看看」这类措辞。

【判定依据——准确优先】
1. 「近期喂养/护理记录」提供事实信号（间隔偏长、进行中偏久、近两日未见等）。
2. 「相关知识摘录」若非空：用通识校准同月龄是否「值得提」；不得把通识写成对方宝宝的记录。
3. 「相关知识摘录」为「（无）」时：禁止编造通识依据；可仅凭清晰史信号谨慎出项，史不够可靠则 items 必须为 []。
4. 禁止为凑列表硬出条目；宁可少出、不出。

你必须只输出一个 JSON 对象（不要 Markdown 代码块，不要其它说明），格式：
{
  "items": [
    {
      "eventId": "事件ID字符串（尽量用记录里的）",
      "eventName": "事件中文名",
      "summaryLine": "跑马灯一行摘要，约 20 字内，含事件名与留意点",
      "followUpPrompt": "家长可原样发给陪伴树洞的追问原文（完整一句/小段中文）",
      "reasons": [
        {
          "type": "elongatedInterval|longActive|suddenAbsence|其它短英文驼峰",
          "score": 0.0到1.0的数,
          "expectationUsed": true或false,
          "ageMonths": 月龄整数或省略,
          "medianGapMs": 毫秒或省略,
          "lastGapMs": 毫秒或省略,
          "expectGapMaxMs": 毫秒或省略,
          "p75DurMs": 毫秒或省略,
          "elapsedMs": 毫秒或省略,
          "expectDurMaxMs": 毫秒或省略,
          "dailyAvg": 数或省略,
          "recent48hCount": 整数或省略,
          "stillExpected": true/false或省略,
          "detailLines": ["可选中文补充说明"]
        }
      ]
    }
  ]
}

规则：
1. 返回列表（可多条），按值得留意程度从高到低；没有可靠依据时 items 可为 []。
2. 每项必须有 eventId、eventName、summaryLine、followUpPrompt、reasons（至少 1 条）。
3. followUpPrompt 必须是家长可直接发送的口语追问，不要命令式「请点击」。
4. 时长类字段一律用毫秒整数；不确定就省略该字段，不要瞎编精确数字。
5. type 优先用 elongatedInterval（间隔偏长）、longActive（进行中偏久）、suddenAbsence（近两日未见）；其它用短驼峰英文。
6. 禁止输出医疗诊断结论或用药建议。
""".strip()


def _format_age(baby_age_months: Optional[int]) -> str:
    """月龄提示词行。"""
    if baby_age_months is None:
        return "宝宝月龄：未知"
    return f"宝宝月龄：{baby_age_months} 个月"


def _compact_knowledge(knowledge_results: List[Dict[str, Any]], *, limit: int = 3) -> str:
    """将已过门槛的向量知识压成短文本块；空则「（无）」。"""
    if not knowledge_results:
        return "（无）"
    lines: List[str] = []
    for i, item in enumerate(knowledge_results[:limit], start=1):
        content = (item.get("content") or "").strip()
        if not content:
            continue
        # 单条截断，控制 token
        if len(content) > 400:
            content = content[:400] + "…"
        score = item.get("score")
        score_part = f" score={score}" if score is not None else ""
        lines.append(f"{i}.{score_part} {content}")
    return "\n".join(lines) if lines else "（无）"


def build_care_alert_user_message(
    *,
    day: str,
    baby_age_months: Optional[int],
    history_events: List[Dict[str, Any]],
    knowledge_results: List[Dict[str, Any]],
    baby_profile: Dict[str, Any],
    history_summary: Any = None,
) -> str:
    """
    组装用户消息：日键、月龄、画像、近史、合格通识。

    业务逻辑：
    仅注入已过向量门槛的 knowledge_results；不附带编排侧 kg_context，
    避免未达标知识硬塞进判定。

    Args:
        day: 上海逻辑日
        baby_age_months: 月龄或 None
        history_events: 原始历史列表
        knowledge_results: 向量检索（已过滤）结果
        baby_profile: 宝宝画像
        history_summary: Go 可选透传历史摘要

    Returns:
        用户消息字符串
    """
    now = shanghai_now()
    slim = slim_history_events_for_prompt(
        history_events,
        limit=40,
        time_style="relative",
        now=now,
    )
    history_json = json.dumps(slim, ensure_ascii=False)
    profile_json = json.dumps(baby_profile or {}, ensure_ascii=False, default=str)
    knowledge_block = _compact_knowledge(knowledge_results)

    parts = [
        f"分析日（Asia/Shanghai）：{day or now.date().isoformat()}",
        f"当前时间：{now.strftime('%Y-%m-%d %H:%M')}",
        _format_age(baby_age_months),
        f"宝宝画像：{profile_json}",
        (
            "请结合「近期记录」的事实信号与「相关知识摘录」（若有）判断今天是否值得留意；"
            "知识为「（无）」时不要编造通识，史不够清楚就返回空 items。严格按系统要求输出 JSON。"
        ),
        f"近期喂养/护理记录（已裁剪）：\n{history_json}",
        f"相关知识摘录（仅向量检索过门槛条目；无为「（无）」）：\n{knowledge_block}",
    ]

    # 仅历史摘要可作补充；不作通识硬塞
    if history_summary not in (None, {}, [], ""):
        try:
            hs = json.dumps(history_summary, ensure_ascii=False, default=str)
        except TypeError:
            hs = str(history_summary)
        if hs and hs not in ("{}", "[]", "null"):
            parts.append(f"编排侧历史摘要（参考，非通识库）：\n{hs}")

    return "\n\n".join(parts)
