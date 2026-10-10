"""
意图向量管理路由

业务说明：
供兄弟仓 Go Hub / voice admin 调用，对 Chroma feeding_intents 做列表、批量写入、
整理重复（document 原文全等）、删除。不写 MySQL；鉴权依赖内网调用。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.feeding.services.intent_cache_store import intent_cache_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/intent-cache", tags=["意图向量管理"])


class IntentCacheBulkItem(BaseModel):
    """单条种子：匹配句 + 载荷。"""

    document: str = Field(..., description="向量文档原文")
    payload: Dict[str, Any] = Field(default_factory=dict, description="意图载荷 JSON")


class IntentCacheBulkRequest(BaseModel):
    """批量灌种请求体（管理端：同 document 跳过而非覆盖）。"""

    items: List[IntentCacheBulkItem] = Field(default_factory=list)


@router.get("")
async def list_intent_cache(
    offset: int = 0,
    limit: int = 100,
) -> Dict[str, Any]:
    """
    分页列出 feeding_intents。

    Query:
        offset / limit（limit 上限 500）
    """
    try:
        return intent_cache_store.list_entries(offset=offset, limit=limit)
    except Exception as exc:
        logger.error("列出意图缓存失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/bulk")
async def bulk_upsert_intent_cache(body: IntentCacheBulkRequest) -> Dict[str, Any]:
    """
    批量灌种：已有相同 document（strip 全等）则跳过，不覆盖。

    Returns:
        ok/added/skipped/failed/ids，供 Hub 弹窗展示新增与跳过。
    """
    entries = [{"document": it.document, "payload": it.payload} for it in body.items]
    try:
        result = intent_cache_store.bulk_upsert(entries)
        logger.info(
            "意图缓存 bulk: added=%s skipped=%s failed=%s",
            result.get("added"),
            len(result.get("skipped") or []),
            len(result.get("failed") or []),
        )
        return result
    except Exception as exc:
        logger.error("bulk 意图缓存失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/dedupe")
async def dedupe_intent_cache() -> Dict[str, Any]:
    """
    整理重复：同 document 每组留一条，删其余。

    Returns:
        kept/deleted/groups，deleted 供 Hub 弹窗列出 id 与 document。
    """
    try:
        result = intent_cache_store.dedupe_exact_documents()
        logger.info(
            "意图缓存 dedupe: kept=%s deleted=%s groups=%s",
            result.get("kept"),
            len(result.get("deleted") or []),
            result.get("groups"),
        )
        return result
    except Exception as exc:
        logger.error("整理意图缓存重复失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/{vector_id}")
async def delete_intent_cache(vector_id: str) -> Dict[str, Any]:
    """按向量 id 删除一条。"""
    ok = intent_cache_store.delete_by_id(vector_id)
    if not ok:
        raise HTTPException(status_code=404, detail="向量不存在或删除失败")
    return {"ok": True, "id": vector_id}
