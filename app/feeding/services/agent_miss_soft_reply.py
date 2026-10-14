"""
覆盖缺口对外软回复

业务说明：
miss 已用硬文案落库后，可选注入预测快照与宝宝画像，经 LLM 生成更自然的对外 content。
无快照不重算；LLM 失败回退硬文案。不影响 fail_kind / 统计。
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from app.feeding.graphs.nodes.prompts.system import AGENT_MISS_SOFT_REPLY_SYSTEM_PROMPT
from app.feeding.services.predict_algo_cache import predict_algo_cache
from app.shared.graphs.stream_llm_collect import stream_llm_collect
from app.shared.http_client import http_client
from app.shared.llm_client import llm_model_config_from_mapping

logger = logging.getLogger(__name__)

_FAIL_KIND_ZH = {
    "event_unresolved": "无法识别对应事件",
    "other_unsupported": "暂不支持该类请求",
    "predict_uncertain": "暂时无法可靠预估时间",
    "segment_unclear": "未听清或需再说一遍",
}


def _baby_profile_brief(profile: Optional[Dict[str, Any]]) -> str:
    """画像摘要；空则空串。"""
    if not isinstance(profile, dict) or not profile:
        return ""
    # 只取常见基础字段，避免整包噪声
    keys = (
        "nickname",
        "name",
        "gender",
        "sex",
        "birthDate",
        "birth_date",
        "months",
        "ageMonths",
        "age_months",
    )
    parts = []
    for k in keys:
        v = profile.get(k)
        if v is not None and str(v).strip():
            parts.append(f"{k}={v}")
    if not parts:
        # 回退：截断 JSON
        try:
            raw = json.dumps(profile, ensure_ascii=False)
            return raw[:800]
        except Exception:
            return ""
    return "; ".join(parts)


async def soft_reply_for_miss(
    *,
    utterance: str,
    hard_content: str,
    fail_kind: str,
    device_no: str,
    llm_model: Optional[Dict[str, Any]] = None,
) -> str:
    """
    生成 miss 对外软回复；失败返回 hard_content。

    Side Effects:
        只读 Redis 预测快照、只读宝宝画像；可能调用 LLM stream。
    """
    hard = (hard_content or "").strip()
    if not hard:
        return hard_content or ""

    snap_block = "（无预测算法快照）"
    try:
        snap = await predict_algo_cache.get(device_no)
        if snap and isinstance(snap.get("by_root"), dict) and snap["by_root"]:
            snap_block = json.dumps(snap, ensure_ascii=False)[:4000]
    except Exception as exc:
        logger.debug("miss 软回复读预测快照跳过: %s", exc)

    baby_block = "（无宝宝基础信息）"
    try:
        profile = await http_client.get_baby_profile(device_no)
        brief = _baby_profile_brief(profile)
        if brief:
            baby_block = brief
    except Exception as exc:
        logger.debug("miss 软回复读画像跳过: %s", exc)

    kind_zh = _FAIL_KIND_ZH.get(fail_kind, fail_kind or "未能完成意图")
    user_payload = (
        f"用户原话：{(utterance or '').strip() or '（空）'}\n"
        f"失败类别：{fail_kind}（{kind_zh}）\n"
        f"规范失败文案：{hard}\n"
        f"预测算法快照：{snap_block}\n"
        f"宝宝基础信息：{baby_block}\n"
        "请生成一句给家长的简短口语回复（说明这次没能可靠完成该意图，"
        "可温和引导换种说法或稍后再试；有快照数字时仅可作不确定参考，"
        "不得假装已给出权威预约/下次时间）。"
    )
    cfg = llm_model_config_from_mapping(llm_model or {})
    try:
        content = await stream_llm_collect(
            messages=[{"role": "user", "content": user_payload}],
            model_config=cfg,
            system_prompt=AGENT_MISS_SOFT_REPLY_SYSTEM_PROMPT,
            node_name="agent_miss_soft_reply",
        )
    except Exception as exc:
        logger.warning("miss 软回复 LLM 失败，回退硬文案: %s", exc)
        return hard
    text = (content or "").strip()
    return text if text else hard
