"""
数量整段飞轮管理路由

业务说明：
供 Hub 对 feeding_qty_cues 做 list/bulk/delete。
payload 须含 quantity（正整数）。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.feeding.services.qty_cue_store import qty_cue_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/qty-cache", tags=["数量飞轮管理"])


class QtyCacheBulkItem(BaseModel):
    document: str = Field(..., description="段整句原文")
    payload: Dict[str, Any] = Field(default_factory=dict)


class QtyCacheBulkRequest(BaseModel):
    items: List[QtyCacheBulkItem] = Field(default_factory=list)


@router.get("")
async def list_qty_cache(offset: int = 0, limit: int = 100) -> Dict[str, Any]:
    try:
        return qty_cue_store.list_entries(offset=offset, limit=limit)
    except Exception as exc:
        logger.error("列出数量飞轮失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/bulk")
async def bulk_qty_cache(body: QtyCacheBulkRequest) -> Dict[str, Any]:
    entries = [{"document": it.document, "payload": it.payload} for it in body.items]
    try:
        return qty_cue_store.bulk_upsert(entries)
    except Exception as exc:
        logger.error("bulk 数量飞轮失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/{vector_id}")
async def delete_qty_cache(vector_id: str) -> Dict[str, Any]:
    ok = qty_cue_store.delete_by_id(vector_id)
    if not ok:
        raise HTTPException(status_code=404, detail="向量不存在或删除失败")
    return {"ok": True, "id": vector_id}
