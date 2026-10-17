"""
覆盖缺口对外回答

业务说明：
miss 已用硬文案落库。对外不再复述失败，只把宝宝画像和预测快照交给模型直接答。
快照没有对应事件时允许按快照猜测。整份快照缺失时先按近 7 日间隔生成再答。
已有快照不重算。模型失败才回退硬文案。
不影响 fail_kind 与统计。
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from app.feeding.graphs.nodes.prompts.system import AGENT_MISS_SOFT_REPLY_SYSTEM_PROMPT
from app.feeding.services.predict_algo_cache import predict_algo_cache
from app.shared.baby_age import format_baby_profile_prompt
from app.shared.graphs.stream_llm_collect import stream_llm_collect
from app.shared.http_client import http_client
from app.shared.llm_client import llm_model_config_from_mapping

logger = logging.getLogger(__name__)

def _baby_profile_brief(profile: Optional[Dict[str, Any]]) -> str:
    """与诊疗同一套名字、性别、月龄；没有画像则空串。"""
    return format_baby_profile_prompt(profile)


async def soft_reply_for_miss(
    *,
    utterance: str,
    hard_content: str,
    fail_kind: str,
    device_no: str,
    llm_model: Optional[Dict[str, Any]] = None,
) -> str:
    """
    用画像和预测快照生成对外回答；模型失败才返回 hard_content。

    fail_kind 只留给上游统计，不写入提示词。

    Side Effects:
        快照缺失时可能拉近 7 日历史并写入 Redis；已有快照只读。
        只读宝宝画像；可能调用 LLM stream。
    """
    del fail_kind
    hard = (hard_content or "").strip()
    if not hard:
        return hard_content or ""

    snap: Optional[Dict[str, Any]] = None
    try:
        snap = await predict_algo_cache.get(device_no)
    except Exception as exc:
        logger.debug("miss 软回复读预测快照跳过: %s", exc)
    by_root = snap.get("by_root") if isinstance(snap, dict) else None
    if not isinstance(by_root, dict) or not by_root:
        # 整份没有才生成。单个根失败或字典为空时仍按无快照继续
        try:
            from app.feeding.services.predict_interval_snapshot import (
                fill_interval_snapshot,
            )

            snap = await fill_interval_snapshot(device_no)
        except Exception as exc:
            logger.warning("miss 软回复补预测快照失败: %s", exc)
            snap = None

    snap_block = "（无预测算法快照）"
    if snap and isinstance(snap.get("by_root"), dict) and snap["by_root"]:
        snap_block = json.dumps(snap, ensure_ascii=False)[:4000]

    baby_block = "（无宝宝基础信息）"
    try:
        profile = await http_client.get_baby_profile(device_no)
        brief = _baby_profile_brief(profile)
        if brief:
            baby_block = brief
    except Exception as exc:
        logger.debug("miss 软回复读画像跳过: %s", exc)

    # 近况是本轮之前的来回；本轮原话单独一行，回答落定后再写入
    recent_block = ""
    try:
        from app.feeding.services.intent_recent_talk import intent_recent_talk_store

        recent_block = await intent_recent_talk_store.prompt_block(device_no)
    except Exception as exc:
        logger.debug("miss 软回复读近况跳过: %s", exc)
    recent_section = (
        f"近三分钟对话（只作背景，不是喂养记录）：\n{recent_block}\n"
        if recent_block
        else ""
    )

    user_payload = (
        f"用户原话：{(utterance or '').strip() or '（空）'}\n"
        f"{recent_section}"
        f"预测算法快照：{snap_block}\n"
        f"{baby_block}\n"
        "请直接回答用户原话。"
    )
    cfg = llm_model_config_from_mapping(llm_model or {})
    try:
        content = await stream_llm_collect(
            messages=[{"role": "user", "content": user_payload}],
            model_config=cfg,
            system_prompt=AGENT_MISS_SOFT_REPLY_SYSTEM_PROMPT,
            node_name="agent_miss_soft_reply",
            thinking_enabled=False,
        )
    except Exception as exc:
        logger.warning("miss 软回复 LLM 失败，回退硬文案: %s", exc)
        return hard
    text = (content or "").strip()
    return text if text else hard
