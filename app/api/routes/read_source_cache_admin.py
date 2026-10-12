"""
R·source 整段飞轮管理路由

业务说明：
供 Hub 对 feeding_read_source_cues 做 list/bulk/delete。
payload 须含 read_source（record|predict）。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.feeding.services.read_source_cue_store import read_source_cue_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/read-source-cache", tags=["R·source飞轮管理"])


class ReadSourceBulkItem(BaseModel):
    document: str = Field(..., description="段整句原文")
    payload: Dict[str, Any] = Field(default_factory=dict)


class ReadSourceBulkRequest(BaseModel):
    items: List[ReadSourceBulkItem] = Field(default_factory=list)


@router.get("")
async def list_read_source_cache(offset: int = 0, limit: int = 100) -> Dict[str, Any]:
    try:
        return read_source_cue_store.list_entries(offset=offset, limit=limit)
    except Exception as exc:
        logger.error("列出 R·source 飞轮失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/bulk")
async def bulk_read_source_cache(body: ReadSourceBulkRequest) -> Dict[str, Any]:
    entries = [{"document": it.document, "payload": it.payload} for it in body.items]
    try:
        return read_source_cue_store.bulk_upsert(entries)
    except Exception as exc:
        logger.error("bulk R·source 飞轮失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/{vector_id}")
async def delete_read_source_cache(vector_id: str) -> Dict[str, Any]:
    ok = read_source_cue_store.delete_by_id(vector_id)
    if not ok:
        raise HTTPException(status_code=404, detail="向量不存在或删除失败")
    return {"ok": True, "id": vector_id}
