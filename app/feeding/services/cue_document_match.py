"""
飞轮按原文精确过滤

业务说明：
运维按一整句 document 查命中。一次取出集合后按去空白的原文相等比较，
不做向量近邻，避免分页把后面的命中漏掉。
"""

from __future__ import annotations

import json
from typing import Any, Dict, List


def filter_entries_by_document(collection: Any, document: str) -> List[Dict[str, Any]]:
    """
    在已初始化的 Chroma 集合里按 trim 后的 document 精确过滤。

    空串直接返回空列表，由路由层拒绝，避免无意义全表扫描从这里发起。
    命中含 id、document、payload。
    """
    key = (document or "").strip()
    if not key:
        return []
    data = collection.get(include=["documents", "metadatas"])
    ids = data.get("ids") or []
    docs = data.get("documents") or []
    metas = data.get("metadatas") or []
    hits: List[Dict[str, Any]] = []
    for i, vid in enumerate(ids):
        raw_doc = docs[i] if i < len(docs) else ""
        if (raw_doc or "").strip() != key:
            continue
        meta = metas[i] or {}
        try:
            payload = json.loads(meta.get("payload") or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        hits.append(
            {
                "id": vid,
                "document": raw_doc if raw_doc is not None else "",
                "payload": payload,
            }
        )
    return hits
