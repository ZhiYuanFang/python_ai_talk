"""
U/D 定位策略飞轮管理路由
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.feeding.services.locate_cue_store import locate_cue_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/locate-cache", tags=["定位策略飞轮管理"])


class LocateBulkItem(BaseModel):
    document: str = Field(..., description="段整句原文")
    payload: Dict[str, Any] = Field(default_factory=dict)


class LocateBulkRequest(BaseModel):
    items: List[LocateBulkItem] = Field(default_factory=list)


@router.get("")
async def list_locate_cache(offset: int = 0, limit: int = 100) -> Dict[str, Any]:
    try:
        return locate_cue_store.list_entries(offset=offset, limit=limit)
    except Exception as exc:
        logger.error("列定位飞轮失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/bulk")
async def bulk_locate_cache(body: LocateBulkRequest) -> Dict[str, Any]:
    entries = [{"document": it.document, "payload": it.payload} for it in body.items]
    try:
        return locate_cue_store.bulk_upsert(entries)
    except Exception as exc:
        logger.error("bulk 定位飞轮失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/{vector_id}")
async def delete_locate_cache(vector_id: str) -> Dict[str, Any]:
    ok = locate_cue_store.delete_by_id(vector_id)
    if not ok:
        raise HTTPException(status_code=404, detail="向量不存在或删除失败")
    return {"ok": True, "id": vector_id}
