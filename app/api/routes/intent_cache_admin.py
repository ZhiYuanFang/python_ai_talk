"""
意图向量管理路由

业务说明：
供兄弟仓 Go Hub / voice admin 调用，对 Chroma feeding_intents 做列表、批量写入、删除。
不写 MySQL；鉴权依赖内网调用（与 /v1/analyze/intent 相同）。
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
    """批量 upsert 请求体。"""

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
    """批量写入或更新种子；确认词 document 会被跳过。"""
    entries = [{"document": it.document, "payload": it.payload} for it in body.items]
    try:
        result = intent_cache_store.bulk_upsert(entries)
        logger.info(
            "意图缓存 bulk: ok=%s failed=%s",
            result.get("ok"),
            len(result.get("failed") or []),
        )
        return result
    except Exception as exc:
        logger.error("bulk 意图缓存失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/{vector_id}")
async def delete_intent_cache(vector_id: str) -> Dict[str, Any]:
    """按向量 id 删除一条。"""
    ok = intent_cache_store.delete_by_id(vector_id)
    if not ok:
        raise HTTPException(status_code=404, detail="向量不存在或删除失败")
    return {"ok": True, "id": vector_id}
