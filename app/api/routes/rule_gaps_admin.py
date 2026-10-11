"""
规则缺口管理路由

业务说明：
供兄弟仓 Go Hub 调用，列出/标已处理规则缺口收件箱。
不写事件向量库；鉴权依赖内网。
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.feeding.services.rule_gap_store import rule_gap_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/rule-gaps", tags=["规则缺口"])


class RuleGapStatusBody(BaseModel):
    """更新缺口状态。"""

    status: str = Field(..., description="如 dismissed / open")


@router.get("")
async def list_rule_gaps(
    offset: int = 0,
    limit: int = 100,
    dimension: str = "",
    status: str = "open",
) -> Dict[str, Any]:
    """
    分页列出规则缺口（默认 open，新→旧）。

    业务说明：
    未指定 dimension 时默认仅 time|quantity（类型/事件/形态飞轮自更新，不进缺口箱）。

    Query:
        offset / limit / dimension / status
    """
    try:
        dim = (dimension or "").strip()
        if not dim:
            # 默认只展 TIME/QTY：分别取再合并按时间排序
            t = rule_gap_store.list_entries(
                offset=0, limit=500, dimension="time", status=status
            )
            q = rule_gap_store.list_entries(
                offset=0, limit=500, dimension="quantity", status=status
            )
            items = list(t.get("items") or []) + list(q.get("items") or [])
            items.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
            start = max(0, int(offset))
            lim = max(1, min(500, int(limit)))
            page = items[start : start + lim]
            return {
                "total": len(items),
                "offset": start,
                "limit": lim,
                "items": page,
            }
        return rule_gap_store.list_entries(
            offset=offset,
            limit=limit,
            dimension=dim,
            status=status,
        )
    except Exception as exc:
        logger.error("列出规则缺口失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.patch("/{gap_id}")
async def patch_rule_gap(gap_id: str, body: RuleGapStatusBody) -> Dict[str, Any]:
    """将缺口标为 dismissed 等。"""
    ok = rule_gap_store.set_status(gap_id, body.status)
    if not ok:
        raise HTTPException(status_code=404, detail="缺口不存在")
    return {"ok": True, "id": gap_id, "status": body.status}
