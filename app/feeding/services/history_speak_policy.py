"""
查史播报策略解析

业务说明：
history 点查前解析 point_pick / open_speak。
常见说法先走本地规则；命中则不查飞轮、不调模型。
未命中才整段飞轮，再小 LLM。禁止静默默认 prefer_completed。
成功且来自模型时仅以段整句回写飞轮（硬切，禁用短词）。
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from app.feeding.graphs.nodes.prompts.system import HISTORY_SPEAK_LLM_PROMPT
from app.feeding.services.dim_rule_lexicon import (
    ELAPSED_WORDS,
    PRIOR_WORDS,
    apply_speak_view,
    words_pattern,
)
from app.feeding.services.event_homophone import cut_segment_pinyin
from app.feeding.services.history_speak_cue_store import (
    as_history_speak_payload,
    history_speak_cue_store,
)
from app.shared.graphs.stream_llm_collect import stream_llm_collect
from app.shared.llm_client import llm_model_config_from_mapping

logger = logging.getLogger(__name__)

_JSON_BLOCK = re.compile(r"\{[\s\S]*\}")

# LLM 失败时的明确降级话术（不得回落无条件优先已完成）
HISTORY_SPEAK_DEGRADE = "暂时无法准确回答上次情况，请稍后再试。"

# 「上次」先于「多久了」，避免「上次睡眠多久」被收成最近一条
_PRIOR_SESSION_RE = words_pattern(PRIOR_WORDS)
_ELAPSED_RE = words_pattern(ELAPSED_WORDS)


def match_local_speak_policy(text: str) -> Optional[Tuple[str, str]]:
    """
    点查播报的本地规则。

    Returns:
        (point_pick, open_speak)；不中返回 None，交给飞轮与模型。
    """
    raw = text or ""
    if _PRIOR_SESSION_RE.search(raw):
        return "prefer_completed", "in_progress"
    if _ELAPSED_RE.search(raw):
        return "latest", "elapsed"
    return None


def _parse_json_obj(content: str) -> Dict[str, Any]:
    """从 LLM 正文解析 JSON 对象。"""
    raw = (content or "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        m = _JSON_BLOCK.search(raw)
        if not m:
            return {}
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return {}
    return data if isinstance(data, dict) else {}


async def llm_resolve_history_speak(
    utterance: str,
    llm_model: Dict[str, Any],
) -> Tuple[Optional[str], Optional[str], List[str]]:
    """
    查史播报小 LLM。

    Returns:
        (point_pick, open_speak, keywords)；非法则为 (None, None, [])
    """
    cfg = llm_model_config_from_mapping(llm_model or {})
    content = await stream_llm_collect(
        messages=[
            {
                "role": "user",
                "content": f"用户原文：{(utterance or '').strip()}",
            }
        ],
        model_config=cfg,
        system_prompt=HISTORY_SPEAK_LLM_PROMPT,
        node_name="history_speak_llm",
        thinking_enabled=False,
    )
    data = _parse_json_obj(content or "")
    clean = as_history_speak_payload(data)
    raw_kws = data.get("keywords")
    keywords: List[str] = []
    if isinstance(raw_kws, list):
        for k in raw_kws:
            s = str(k or "").strip()
            if s and s not in keywords:
                keywords.append(s)
    if not clean:
        logger.warning("查史播报 LLM 输出非法: %s", (content or "")[:200])
        return None, None, []
    return clean["point_pick"], clean["open_speak"], keywords


async def resolve_history_speak_policy(
    utterance: str,
    llm_model: Dict[str, Any],
) -> Optional[Tuple[str, str]]:
    """
    解析点查策略两维：本地规则 → 整段飞轮 → LLM；失败返回 None。

    本地规则命中不查飞轮、不回写。来自 LLM 时仅以段整句原文写入飞轮。
    """
    text = (utterance or "").strip()
    # 本地规则看播报视图；飞轮和模型仍用原文
    rule_text = apply_speak_view(text, cut_segment_pinyin(text))
    local = match_local_speak_policy(rule_text)
    if local is not None:
        logger.info(
            "查史播报本地规则: pick=%s open=%s text=%s",
            local[0],
            local[1],
            text[:40],
        )
        return local
    hit = history_speak_cue_store.search_policy(text)
    if hit is not None:
        logger.info(
            "查史播报飞轮命中: pick=%s open=%s text=%s",
            hit[0],
            hit[1],
            text[:40],
        )
        return hit

    pp, os_, keywords = await llm_resolve_history_speak(text, llm_model)
    if not pp or not os_:
        return None

    # 硬切：只回写整段原文；忽略 keywords 短词列表
    _ = keywords
    vid = history_speak_cue_store.add(
        text, {"point_pick": pp, "open_speak": os_}
    )
    logger.info(
        "查史播报飞轮整段回写: id=%s pick=%s open=%s",
        vid,
        pp,
        os_,
    )
    return pp, os_
