"""
九个喂养飞轮按原文聚合查询

业务说明：
GET /v1/admin/cues/by-document 按 trim 后的整句精确列出命中。
任一集合失败则整次 500，避免把缺的维度当成没有这条。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from fastapi import APIRouter, HTTPException

from app.feeding.services.history_speak_cue_store import (
    COLLECTION_NAME as HISTORY_SPEAK_COLLECTION,
    history_speak_cue_store,
)
from app.feeding.services.intent_cache_store import (
    COLLECTION_NAME as INTENT_COLLECTION,
    intent_cache_store,
)
from app.feeding.services.locate_cue_store import (
    COLLECTION_NAME as LOCATE_COLLECTION,
    locate_cue_store,
)
from app.feeding.services.op_cue_store import (
    COLLECTION_NAME as OP_COLLECTION,
    op_cue_store,
)
from app.feeding.services.predict_cue_store import (
    COLLECTION_NAME as PREDICT_COLLECTION,
    predict_cue_store,
)
from app.feeding.services.qty_cue_store import (
    COLLECTION_NAME as QTY_COLLECTION,
    qty_cue_store,
)
from app.feeding.services.read_source_cue_store import (
    COLLECTION_NAME as READ_SOURCE_COLLECTION,
    read_source_cue_store,
)
from app.feeding.services.remark_cue_store import (
    COLLECTION_NAME as REMARK_COLLECTION,
    remark_cue_store,
)
from app.feeding.services.time_cue_store import (
    COLLECTION_NAME as TIME_COLLECTION,
    time_cue_store,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/cues", tags=["飞轮原文查询"])

# 维度键与 Go 删除接口对应；顺序固定，便于对照
_SOURCES: Tuple[Tuple[str, str, Any], ...] = (
    ("op", OP_COLLECTION, op_cue_store),
    ("intent", INTENT_COLLECTION, intent_cache_store),
    ("qty", QTY_COLLECTION, qty_cue_store),
    ("time", TIME_COLLECTION, time_cue_store),
    ("remark", REMARK_COLLECTION, remark_cue_store),
    ("read_source", READ_SOURCE_COLLECTION, read_source_cue_store),
    ("predict", PREDICT_COLLECTION, predict_cue_store),
    ("history_speak", HISTORY_SPEAK_COLLECTION, history_speak_cue_store),
    ("locate", LOCATE_COLLECTION, locate_cue_store),
)


@router.get("/by-document")
async def cues_by_document(document: str = "") -> Dict[str, Any]:
    """
    按整句原文精确查询九个飞轮。

    document 去空白后为空则 400，不扫库。
    """
    key = (document or "").strip()
    if not key:
        raise HTTPException(status_code=400, detail="document 不能为空")
    items: List[Dict[str, Any]] = []
    try:
        for dimension, collection, store in _SOURCES:
            for hit in store.find_by_document(key):
                items.append(
                    {
                        "dimension": dimension,
                        "collection": collection,
                        "id": hit.get("id") or "",
                        "document": hit.get("document") or "",
                        "payload": hit.get("payload") if isinstance(hit.get("payload"), dict) else {},
                    }
                )
    except Exception as exc:
        logger.error("按原文查询飞轮失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="飞轮查询失败") from exc
    return {"items": items}
