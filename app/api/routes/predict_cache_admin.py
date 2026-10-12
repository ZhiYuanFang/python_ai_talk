"""
R·predict 两维飞轮管理路由
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.feeding.services.predict_cue_store import predict_cue_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/predict-cache", tags=["预测两维飞轮管理"])


class PredictBulkItem(BaseModel):
    document: str = Field(..., description="段整句原文")
    payload: Dict[str, Any] = Field(default_factory=dict)


class PredictBulkRequest(BaseModel):
    items: List[PredictBulkItem] = Field(default_factory=list)


@router.get("")
async def list_predict_cache(offset: int = 0, limit: int = 100) -> Dict[str, Any]:
    try:
        return predict_cue_store.list_entries(offset=offset, limit=limit)
    except Exception as exc:
        logger.error("列出预测飞轮失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/bulk")
async def bulk_predict_cache(body: PredictBulkRequest) -> Dict[str, Any]:
    entries = [{"document": it.document, "payload": it.payload} for it in body.items]
    try:
        return predict_cue_store.bulk_upsert(entries)
    except Exception as exc:
        logger.error("bulk 预测飞轮失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/{vector_id}")
async def delete_predict_cache(vector_id: str) -> Dict[str, Any]:
    ok = predict_cue_store.delete_by_id(vector_id)
    if not ok:
        raise HTTPException(status_code=404, detail="向量不存在或删除失败")
    return {"ok": True, "id": vector_id}
