"""
类型关键字向量管理路由

业务说明：
供兄弟仓 Go Hub 调用，对 Chroma feeding_type_cues 做列表、批量写入、
整理重复、删除。payload 须为 {target_type, op, history_mode}。
不写 MySQL；鉴权依赖内网调用。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.feeding.services.type_cue_store import type_cue_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/type-cache", tags=["类型向量管理"])


class TypeCacheBulkItem(BaseModel):
    """单条种子：关键字 + 类型载荷。"""

    document: str = Field(..., description="类型关键字原文")
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="须含 target_type；可选 op、history_mode",
    )


class TypeCacheBulkRequest(BaseModel):
    """批量灌种（同 document 跳过）。"""

    items: List[TypeCacheBulkItem] = Field(default_factory=list)


@router.get("")
async def list_type_cache(
    offset: int = 0,
    limit: int = 100,
) -> Dict[str, Any]:
    """分页列出 feeding_type_cues（created_at 新→旧）。"""
    try:
        return type_cue_store.list_entries(offset=offset, limit=limit)
    except Exception as exc:
        logger.error("列出类型缓存失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/bulk")
async def bulk_upsert_type_cache(body: TypeCacheBulkRequest) -> Dict[str, Any]:
    """批量灌种：已有相同 document 则跳过。"""
    entries = [{"document": it.document, "payload": it.payload} for it in body.items]
    try:
        result = type_cue_store.bulk_upsert(entries)
        logger.info(
            "类型缓存 bulk: added=%s skipped=%s failed=%s",
            result.get("added"),
            len(result.get("skipped") or []),
            len(result.get("failed") or []),
        )
        return result
    except Exception as exc:
        logger.error("bulk 类型缓存失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/dedupe")
async def dedupe_type_cache() -> Dict[str, Any]:
    """整理重复 document。"""
    try:
        result = type_cue_store.dedupe_exact_documents()
        logger.info(
            "类型缓存 dedupe: kept=%s deleted=%s groups=%s",
            result.get("kept"),
            len(result.get("deleted") or []),
            result.get("groups"),
        )
        return result
    except Exception as exc:
        logger.error("整理类型缓存重复失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/{vector_id}")
async def delete_type_cache(vector_id: str) -> Dict[str, Any]:
    """按向量 id 删除一条。"""
    ok = type_cue_store.delete_by_id(vector_id)
    if not ok:
        raise HTTPException(status_code=404, detail="向量不存在或删除失败")
    return {"ok": True, "id": vector_id}
