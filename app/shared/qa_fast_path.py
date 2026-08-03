"""
Q&A 捷径：命中判定、改写、入库推广

业务说明：
改写独立问句后检索全局 qa_fast_path；sim/quality/age_band 全过才 hit。
隐式 accepted 且上轮改写成功时 upsert。
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from app.config.settings import settings
from app.shared.llm_client import LLMModelConfig, llm_client

logger = logging.getLogger(__name__)

# 轻量敏感拦截：命中则强制 miss（不做捷径复用）
_SENSITIVE_PATTERNS = (
    r"用药剂量",
    r"吃多少毫克",
    r"处方",
    r"抗生素.*剂量",
    r"诊断.*病",
    r"是不是得了",
)


def is_block_fast_path(state: Dict[str, Any]) -> Tuple[bool, str]:
    """
    是否强制跳过 Q&A 捷径。

    Returns:
        (blocked, reason)
    """
    if not bool(settings.qa_fast_path_enabled):
        return True, "feature_disabled"
    if state.get("force_needs_history"):
        return True, "force_needs_history"
    if state.get("skip_knowledge"):
        # history 点查与捷径互斥
        return True, "skip_knowledge_history"
    if state.get("block_fast_path"):
        return True, "block_fast_path_flag"

    question = str(state.get("question") or state.get("user_input") or "")
    for pat in _SENSITIVE_PATTERNS:
        if re.search(pat, question):
            return True, f"sensitive:{pat}"
    return False, ""


def evaluate_qa_hit(
    candidates: List[Dict[str, Any]],
    *,
    age_band: Optional[str],
    sim_threshold: Optional[float] = None,
    quality_min: Optional[float] = None,
) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    从候选中挑第一条合格 hit。

    Returns:
        (hit_dict_or_None, miss_reason)
        hit_dict 含 id/score/answer/standalone_question/age_band/quality_score
    """
    sim_th = float(
        sim_threshold if sim_threshold is not None else settings.qa_sim_threshold
    )
    q_min = float(quality_min if quality_min is not None else settings.qa_quality_min)

    if not age_band:
        logger.info("Q&A 命中判定: miss reason=unknown_age")
        return None, "unknown_age"
    if not candidates:
        logger.info("Q&A 命中判定: miss reason=no_candidates age_band=%s", age_band)
        return None, "no_candidates"

    for item in candidates:
        score = float(item.get("score") or 0.0)
        meta = item.get("metadata") or {}
        if not isinstance(meta, dict):
            meta = {}
        item_band = str(meta.get("age_band") or "")
        quality = float(meta.get("quality_score", 0.8))
        answer = str(meta.get("answer") or "").strip()
        reasons = []
        if score <= sim_th:
            reasons.append(f"sim={score:.4f}<={sim_th}")
        if quality < q_min:
            reasons.append(f"quality={quality:.4f}<{q_min}")
        if item_band != age_band:
            reasons.append(f"age_band={item_band!r}!={age_band!r}")
        if not answer:
            reasons.append("empty_answer")
        if reasons:
            logger.info(
                "Q&A 候选未命中: id=%s, %s",
                item.get("id"),
                "; ".join(reasons),
            )
            continue
        hit = {
            "id": item.get("id"),
            "score": score,
            "answer": answer,
            "standalone_question": str(
                meta.get("standalone_question") or item.get("content") or ""
            ),
            "age_band": item_band,
            "quality_score": quality,
        }
        logger.info(
            "Q&A 命中: id=%s, sim=%.4f, quality=%.4f, age_band=%s, question=%r",
            hit["id"],
            score,
            quality,
            item_band,
            hit["standalone_question"][:80],
        )
        return hit, "hit"

    logger.info(
        "Q&A 命中判定: miss reason=thresholds age_band=%s top_sim=%s",
        age_band,
        candidates[0].get("score") if candidates else None,
    )
    return None, "thresholds"


async def rewrite_standalone_question(
    question: str,
    chat_context: str,
    model_config: Dict[str, Any],
    *,
    timeout_s: Optional[float] = None,
) -> Optional[str]:
    """
    多轮 → 独立问句；失败/超时返回 None（调用方视为 miss，不回退原文检索）。
    """
    q = (question or "").strip()
    if not q:
        logger.info("问句改写 miss: empty_question")
        return None

    timeout = float(
        timeout_s if timeout_s is not None else settings.rewrite_timeout_s
    )
    system_prompt = (
        "你把家长在多轮对话中的本轮问题改写成一条可独立检索的中文问句。"
        "只输出问句本身，不要解释，不要引号。"
        "若本轮已是独立问句，原样精简输出。"
    )
    user_message = (
        f"近期对话：\n{(chat_context or '')[:1200] or '（无）'}\n\n"
        f"家长本轮：\n{q[:500]}"
    )
    cfg = LLMModelConfig(
        provider=model_config.get("provider", "deepseek"),
        name=model_config.get("name", "deepseek-chat"),
        max_in_flight=int(model_config.get("max_in_flight") or 3),
    )

    async def _invoke() -> str:
        resp = await llm_client.invoke(
            messages=[{"role": "user", "content": user_message}],
            model_config=cfg,
            system_prompt=system_prompt,
        )
        return (resp.content or "").strip()

    try:
        text = await asyncio.wait_for(_invoke(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.info("问句改写 miss: timeout=%.2fs question=%r", timeout, q[:80])
        return None
    except Exception as e:
        logger.warning("问句改写 miss: error=%s question=%r", e, q[:80])
        return None

    # 去掉可能的引号/前缀
    text = text.strip().strip("「」\"'")
    if text.startswith("问句：") or text.startswith("问句:"):
        text = text.split(":", 1)[-1].strip()
    if not text:
        logger.info("问句改写 miss: empty_llm_output question=%r", q[:80])
        return None
    logger.info("问句改写成功: %r -> %r", q[:80], text[:80])
    return text


def promote_accepted_qa(
    *,
    standalone_question: Optional[str],
    answer: Optional[str],
    age_band: Optional[str],
) -> Optional[str]:
    """accepted 后写入 Q&A；缺字段则跳过并打日志。"""
    from app.shared.vector_store import vector_store

    q = (standalone_question or "").strip()
    a = (answer or "").strip()
    band = (age_band or "").strip()
    if not q:
        logger.info("Q&A 推广跳过: 无 standalone_question")
        return None
    if not a:
        logger.info("Q&A 推广跳过: 无 answer")
        return None
    if not band:
        logger.info("Q&A 推广跳过: 无 age_band")
        return None
    return vector_store.upsert_qa(
        standalone_question=q,
        answer=a,
        age_band=band,
        quality_score=0.8,
    )
