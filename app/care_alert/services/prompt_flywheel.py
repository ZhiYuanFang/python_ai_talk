"""
护理留意 prompt 飞轮：反馈账本 → 对比样例重写

业务说明：
固定意图 ignore|follow_up 写入 ledger 后，按阈值将账本聚合为对比样例块并写回 prompt.json。
冲突同类反馈保留 ✓ / ✗ / ⚡ 张力，不净票抹平；超长则裁剪或中止写保留旧文件。
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Any, Dict, List, Tuple

from app.care_alert.services import prompt_store
from app.config.settings import settings

logger = logging.getLogger(__name__)


def _min_evidence() -> int:
    return max(1, int(getattr(settings, "care_alert_flywheel_min_evidence", 2) or 2))


def _max_chars() -> int:
    return max(200, int(getattr(settings, "care_alert_examples_max_chars", 1200) or 1200))


def _rewrite_every() -> int:
    return max(1, int(getattr(settings, "care_alert_flywheel_rewrite_every", 20) or 20))


def _rewrite_min_interval_s() -> int:
    return max(0, int(getattr(settings, "care_alert_flywheel_rewrite_min_interval_s", 3600) or 3600))


def should_rewrite() -> bool:
    """
    是否应触发对比样例重写。

    业务逻辑：
    - 自上次重写以来新增条数 >= N，或
    - 距上次重写已超过最小间隔且有新增条数
    """
    meta = prompt_store.load_flywheel_meta()
    since = int(meta.get("entries_since_rewrite") or 0)
    if since <= 0:
        return False
    if since >= _rewrite_every():
        return True
    last_at = int(meta.get("last_rewrite_at") or 0)
    if last_at <= 0:
        return since >= _rewrite_every()
    elapsed = int(time.time()) - last_at
    return elapsed >= _rewrite_min_interval_s() and since > 0


def _aggregate_slots(
    entries: List[Dict[str, Any]],
) -> Dict[Tuple[str, str], Dict[str, int]]:
    """
    按 (reason_type|eventName, 信号档) 聚合 follow_up / ignore 计数。

    Returns:
        {(type_key, band): {"follow_up": n, "ignore": m}}
    """
    slots: Dict[Tuple[str, str], Dict[str, int]] = defaultdict(
        lambda: {"follow_up": 0, "ignore": 0}
    )
    for e in entries:
        intent = str(e.get("intent") or "").strip()
        if intent not in ("follow_up", "ignore"):
            continue
        type_key = str(e.get("reason_type") or e.get("event_name") or "other").strip()
        if not type_key:
            type_key = "other"
        band = str(e.get("score_band") or "weak").strip().lower()
        if band not in ("strong", "weak"):
            band = "weak"
        slots[(type_key, band)][intent] += 1
    return slots


def render_contrastive_examples(entries: List[Dict[str, Any]]) -> str:
    """
    将 ledger 聚合成对比样例文本（含长度裁剪）。

    业务逻辑：
    - 单侧证据 >= k 且对侧不足 → ✓ 或 ✗
    - 两侧均 >= k → ⚡ 张力行（不抹平）
    - 两侧均 < k → 省略
    """
    k = _min_evidence()
    slots = _aggregate_slots(entries)
    prefer: List[str] = []
    avoid: List[str] = []
    tension: List[str] = []

    for (type_key, band), counts in sorted(slots.items()):
        fu = int(counts.get("follow_up") or 0)
        ig = int(counts.get("ignore") or 0)
        if fu < k and ig < k:
            continue
        band_label = "强信号" if band == "strong" else "弱信号"
        if fu >= k and ig >= k:
            tension.append(
                f"- {type_key}｜{band_label}：follow_up={fu} / ignore={ig} → "
                f"保留张力：强偏离或证据足时宜提，弱偏离时轻提（有近两日记录时勿全部不提）"
            )
        elif fu >= k:
            prefer.append(
                f"- 类型: {type_key}｜信号: {band_label}（follow_up={fu}）→ 更宜提出"
            )
        else:
            avoid.append(
                f"- 类型: {type_key}｜信号: {band_label}（ignore={ig}）→ 宜轻提"
                f"（温和语气、偏低 score；有近两日记录时不要理解成禁提）"
            )

    if not prefer and not avoid and not tension:
        return ""

    parts = [
        "【用户反馈对比样例｜请归纳条件，勿死记个案；非当前宝宝记录】",
        "说明：有近两日记录时不得建议「全部不提」；弱信号对应轻提而非禁提。",
    ]
    if prefer:
        parts.append("✓ 更宜提出（follow_up 居多）")
        parts.extend(prefer)
    if avoid:
        parts.append("✗ 宜轻提 / 易被忽略时仍可温和提出（ignore 居多）")
        parts.extend(avoid)
    if tension:
        parts.append("⚡ 同类相反（保留张力，勿合并成一句净票）")
        parts.extend(tension)

    text = "\n".join(parts)
    max_chars = _max_chars()
    if len(text) <= max_chars:
        return text

    # 超限：优先保留张力与较短列表，逐行截断
    logger.warning(
        "护理留意对比样例超长(%s>%s)，裁剪",
        len(text),
        max_chars,
    )
    lines = text.splitlines()
    kept: List[str] = []
    for line in lines:
        candidate = "\n".join(kept + [line])
        if len(candidate) > max_chars:
            break
        kept.append(line)
    trimmed = "\n".join(kept).strip()
    if not trimmed:
        # 极端情况：首行都超长，硬截断
        return text[: max_chars - 1] + "…"
    return trimmed


def maybe_rewrite_prompt_from_ledger(*, force: bool = False) -> bool:
    """
    条件满足时根据 ledger 重写 contrastive_examples 并落盘。

    Args:
        force: True 则忽略阈值强制尝试

    Returns:
        True 表示已成功写入新 prompt；False 表示跳过或失败（旧文件保留）
    """
    if not force and not should_rewrite():
        return False

    entries = prompt_store.read_ledger_entries()
    examples = render_contrastive_examples(entries)
    doc = prompt_store.load_or_bootstrap_prompt()
    new_doc = dict(doc)
    new_doc["contrastive_examples"] = examples
    # 保留原 output_format / guidance；禁止被样例污染
    if not prompt_store.save_prompt_document(new_doc):
        logger.warning("护理留意飞轮重写失败，保留旧 prompt")
        return False

    meta = prompt_store.load_flywheel_meta()
    meta["last_rewrite_at"] = int(time.time())
    meta["entries_since_rewrite"] = 0
    prompt_store.save_flywheel_meta(meta)
    logger.info(
        "护理留意飞轮已重写对比样例: chars=%s entries=%s",
        len(examples),
        len(entries),
    )
    return True


def record_feedback_and_maybe_rewrite(entry: Dict[str, Any]) -> None:
    """
    追加 ledger 并按阈值尝试重写 prompt。

    Side Effects:
        写 ledger / 可能写 prompt.json；异常由调用方捕获 ACK
    """
    prompt_store.append_ledger_entry(entry)
    maybe_rewrite_prompt_from_ledger(force=False)
