"""
备注整段飞轮管理路由

业务说明：
供 Hub 对 feeding_remark_cues 做 list/bulk/delete。
payload 须含 remark（允许空字符串）。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.feeding.services.remark_cue_store import remark_cue_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/remark-cache", tags=["备注飞轮管理"])


class RemarkCacheBulkItem(BaseModel):
    document: str = Field(..., description="段整句原文")
    payload: Dict[str, Any] = Field(default_factory=dict)


class RemarkCacheBulkRequest(BaseModel):
    items: List[RemarkCacheBulkItem] = Field(default_factory=list)


@router.get("")
async def list_remark_cache(offset: int = 0, limit: int = 100) -> Dict[str, Any]:
    try:
        return remark_cue_store.list_entries(offset=offset, limit=limit)
    except Exception as exc:
        logger.error("列出备注飞轮失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/bulk")
async def bulk_remark_cache(body: RemarkCacheBulkRequest) -> Dict[str, Any]:
    entries = [{"document": it.document, "payload": it.payload} for it in body.items]
    try:
        return remark_cue_store.bulk_upsert(entries)
    except Exception as exc:
        logger.error("bulk 备注飞轮失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/{vector_id}")
async def delete_remark_cache(vector_id: str) -> Dict[str, Any]:
    ok = remark_cue_store.delete_by_id(vector_id)
    if not ok:
        raise HTTPException(status_code=404, detail="向量不存在或删除失败")
    return {"ok": True, "id": vector_id}
