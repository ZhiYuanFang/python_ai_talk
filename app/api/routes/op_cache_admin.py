"""
OP 轨整段飞轮管理路由

业务说明：
供 Hub 对 feeding_op_cues 做 list/bulk/delete。
payload 须含 op_rail（create|read|update|delete|exit|other）。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.feeding.services.op_cue_store import op_cue_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/op-cache", tags=["OP轨飞轮管理"])


class OpCacheBulkItem(BaseModel):
    document: str = Field(..., description="段整句原文")
    payload: Dict[str, Any] = Field(default_factory=dict)


class OpCacheBulkRequest(BaseModel):
    items: List[OpCacheBulkItem] = Field(default_factory=list)


@router.get("")
async def list_op_cache(offset: int = 0, limit: int = 100) -> Dict[str, Any]:
    try:
        return op_cue_store.list_entries(offset=offset, limit=limit)
    except Exception as exc:
        logger.error("列出 OP 飞轮失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/bulk")
async def bulk_op_cache(body: OpCacheBulkRequest) -> Dict[str, Any]:
    entries = [{"document": it.document, "payload": it.payload} for it in body.items]
    try:
        return op_cue_store.bulk_upsert(entries)
    except Exception as exc:
        logger.error("bulk OP 飞轮失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/{vector_id}")
async def delete_op_cache(vector_id: str) -> Dict[str, Any]:
    ok = op_cue_store.delete_by_id(vector_id)
    if not ok:
        raise HTTPException(status_code=404, detail="向量不存在或删除失败")
    return {"ok": True, "id": vector_id}
