"""
时间相对配方飞轮管理路由

业务说明：
供 Hub 对 feeding_time_cues 做 list/bulk/delete。
payload 须为合法相对配方；拒绝仅含绝对 Unix 的条目。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.feeding.services.time_cue_store import time_cue_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/time-cache", tags=["时间飞轮管理"])


class TimeCacheBulkItem(BaseModel):
    document: str = Field(..., description="段整句原文")
    payload: Dict[str, Any] = Field(default_factory=dict)


class TimeCacheBulkRequest(BaseModel):
    items: List[TimeCacheBulkItem] = Field(default_factory=list)


@router.get("")
async def list_time_cache(offset: int = 0, limit: int = 100) -> Dict[str, Any]:
    try:
        return time_cue_store.list_entries(offset=offset, limit=limit)
    except Exception as exc:
        logger.error("列出时间飞轮失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/bulk")
async def bulk_time_cache(body: TimeCacheBulkRequest) -> Dict[str, Any]:
    entries = [{"document": it.document, "payload": it.payload} for it in body.items]
    try:
        return time_cue_store.bulk_upsert(entries)
    except Exception as exc:
        logger.error("bulk 时间飞轮失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/{vector_id}")
async def delete_time_cache(vector_id: str) -> Dict[str, Any]:
    ok = time_cue_store.delete_by_id(vector_id)
    if not ok:
        raise HTTPException(status_code=404, detail="向量不存在或删除失败")
    return {"ok": True, "id": vector_id}
