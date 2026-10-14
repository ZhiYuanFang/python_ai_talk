"""
覆盖缺口（答不出）管理路由

业务说明：
供兄弟仓 Go Hub 列出/删除终局失败问答记录。
独立于规则缺口与时间飞轮；鉴权依赖内网。
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from app.feeding.services.agent_miss_store import agent_miss_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/miss-inbox", tags=["覆盖缺口"])


@router.get("")
async def list_miss_inbox(
    offset: int = 0,
    limit: int = 100,
    status: str = "open",
    fail_kind: str = "",
) -> Dict[str, Any]:
    """分页列出覆盖缺口（默认 open，新→旧）。"""
    try:
        return agent_miss_store.list_entries(
            offset=offset,
            limit=limit,
            status=status,
            fail_kind=fail_kind,
        )
    except Exception as exc:
        logger.error("列出覆盖缺口失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/{miss_id}")
async def delete_miss_inbox(miss_id: str) -> Dict[str, Any]:
    """删除一条覆盖缺口。"""
    ok = agent_miss_store.delete_by_id(miss_id)
    if not ok:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"ok": True, "id": miss_id}
