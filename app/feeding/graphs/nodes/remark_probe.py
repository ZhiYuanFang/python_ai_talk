"""
备注探针节点

业务说明：
点查句式且用户词不在事件字典时，用 Go filter 备注模糊（小 limit）
聚合成一行摘要，供分类 LLM 看见「AD 挂在营养品下」。
不把原始行列表注入 prompt。
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from typing import Any, Dict, List, Optional

from app.feeding.utils.query_utterance import looks_like_history_query
from app.shared.history_window import enum_to_unix
from app.shared.http_client import http_client

logger = logging.getLogger(__name__)

# 从点查句里剥掉问句套话，剩下的当备注候选
_STRIP_RE = re.compile(
    r"上一次|上次|最近一次|什么时候|啥时候|何时|吃的|喝的|吃了|喝了|"
    r"查一下|查查|分别|是|的|了|呢|吗|呀|啊|\s+",
)


def extract_oov_token(text: str, event_names: List[str]) -> Optional[str]:
    """抽出不在字典里的专名候选。"""
    t = (text or "").strip()
    leftover = _STRIP_RE.sub("", t)
    leftover = leftover.strip("？?。．.!！，,、")
    if not leftover or len(leftover) > 20:
        return None
    names = {n.strip() for n in event_names if n and n.strip()}
    if leftover in names:
        return None
    for n in names:
        if leftover in n or n in leftover:
            return None
    return leftover


def _summarize_hits(rows: List[Dict[str, Any]], keyword: str) -> str:
    """聚合成一行：事件名 × 次数，最近时间。"""
    names: List[str] = []
    latest = ""
    for row in rows:
        name = str(row.get("eventName") or row.get("event_name") or "")
        if name:
            names.append(name)
        if not latest:
            latest = str(row.get("startTime") or row.get("start_time") or "")
    if not names:
        return f"备注含 {keyword}：近窗无命中"
    counts = Counter(names)
    parts = [f"{n} ×{c}" for n, c in counts.most_common()]
    extra = f"，最近 {latest}" if latest else ""
    return f"备注含 {keyword}：{'、'.join(parts)}{extra}"


async def remark_probe(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    可选备注探针。

    非点查或缓存已命中则跳过。
    """
    if state.get("intent_cache_hit"):
        return {}
    text = state.get("user_input") or ""
    if not looks_like_history_query(text):
        return {"remark_probe_hint": ""}
    dictionary = state.get("event_dictionary") or []
    names = [str(e.get("event_name") or "") for e in dictionary]
    token = extract_oov_token(text, names)
    if not token:
        return {"remark_probe_hint": ""}
    device_no = state.get("device_no") or ""
    start_time, end_time = enum_to_unix("last_30_days")
    try:
        rows = await http_client.get_filtered_history_events(
            device_no=device_no,
            event_ids=None,
            start_time=start_time,
            end_time=end_time,
            limit=10,
            remark=token,
        )
    except Exception as exc:
        logger.warning(f"备注探针失败: {exc}")
        return {"remark_probe_hint": "", "remark_keyword": token}
    hint = _summarize_hits(rows or [], token)
    logger.info(f"备注探针: token={token}, hint={hint}")
    return {
        "remark_probe_hint": hint,
        "remark_keyword": token,
    }
