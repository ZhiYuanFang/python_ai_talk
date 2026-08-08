"""
护理留意分析提示词

业务说明：
引导 LLM 基于月龄、近期记录与知识，产出「值得留意」JSON 列表。
语气非医疗诊断；每项必须含 followUpPrompt。
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.shared.history_prompt_fields import slim_history_events_for_prompt
from app.tip.graphs.nodes.derive_baby_age import shanghai_now


def build_care_alert_system_prompt() -> str:
    """
    系统提示词：角色与硬输出格式。

    Returns:
        系统提示词字符串
    """
    return """
你是一位有经验的母婴闺蜜，帮家长从「近期喂养/护理记录」里找出今天「值得留意」的点。
态度：温和提醒、不是诊断、不开药、不恐吓。可用「值得留意」「可以多看看」这类措辞。

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
    """将向量知识压成短文本块。"""
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
    kg_context: Any = None,
) -> str:
    """
    组装用户消息：日键、月龄、画像、近史、知识。

    Args:
        day: 上海逻辑日
        baby_age_months: 月龄或 None
        history_events: 原始历史列表
        knowledge_results: 向量检索结果
        baby_profile: 宝宝画像
        history_summary: Go 可选透传摘要
        kg_context: Go 可选透传知识上下文

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

    parts = [
        f"分析日（Asia/Shanghai）：{day or now.date().isoformat()}",
        f"当前时间：{now.strftime('%Y-%m-%d %H:%M')}",
        _format_age(baby_age_months),
        f"宝宝画像：{profile_json}",
        "请根据下列近期记录与知识，找出今天值得留意的护理点，并严格按系统要求输出 JSON。",
        f"近期喂养/护理记录（已裁剪）：\n{history_json}",
        f"相关知识摘录：\n{_compact_knowledge(knowledge_results)}",
    ]

    # Go 透传上下文：非空时附加，便于编排侧预拼
    if history_summary not in (None, {}, [], ""):
        try:
            hs = json.dumps(history_summary, ensure_ascii=False, default=str)
        except TypeError:
            hs = str(history_summary)
        if hs and hs not in ("{}", "[]", "null"):
            parts.append(f"编排侧历史摘要（参考）：\n{hs}")

    if kg_context not in (None, {}, [], ""):
        try:
            kg = json.dumps(kg_context, ensure_ascii=False, default=str)
        except TypeError:
            kg = str(kg_context)
        if kg and kg not in ("{}", "[]", "null"):
            parts.append(f"编排侧知识上下文（参考）：\n{kg}")

    return "\n\n".join(parts)
