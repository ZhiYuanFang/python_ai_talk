"""
History tools 编排：鉴权 A → 查 URL → 上游 → 塑形

业务说明：
插件只打本模块 HTTP；缺 A 或未配 URL 明确失败，无默认 Go。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import Header, HTTPException

from app.agent_console import repository as repo
from app.agent_console.catalog import catalog_by_key
from app.agent_console import shaping
from app.agent_console.upstream import call_upstream

API_TOKEN_HEADER = "x-pangbao-api-token"


def require_pair_from_a(a_token: Optional[str]) -> Dict[str, Any]:
    """解析 A；无效则 401。"""
    raw = (a_token or "").strip()
    if not raw:
        raise HTTPException(status_code=401, detail="缺少 API Token（x-pangbao-api-token），无法 CRUD/读史")
    pair = repo.find_pair_by_a(raw)
    if not pair:
        raise HTTPException(status_code=401, detail="API Token 无效或已停用")
    return pair


async def run_tool(
    tool_key: str,
    *,
    a_token: Optional[str],
    json_body: Any = None,
    query: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    执行已注册槽位。

    Args:
        tool_key: Catalog key
        a_token: 请求头中的 A
        json_body: POST JSON
        query: GET query
    """
    pair = require_pair_from_a(a_token)
    cat = catalog_by_key().get(tool_key)
    if not cat:
        return {"ok": False, "error": f"未知 tool: {tool_key}"}
    ep = repo.get_endpoint(int(pair["id"]), tool_key)
    if not ep or not (ep.get("url") or "").strip():
        return {
            "ok": False,
            "error": f"未配置 tool「{tool_key}」的完整 URL，请在 API 管理页配置",
        }
    method = (ep.get("method") or cat.get("method") or "POST").upper()
    bearer = (ep.get("upstream_auth") or "").strip()
    upstream = await call_upstream(
        method,
        ep["url"],
        json_body=json_body if method != "GET" else None,
        query=query if method == "GET" else None,
        bearer=bearer,
    )
    if not upstream.get("ok"):
        return {
            "ok": False,
            "error": upstream.get("error") or "上游失败",
            "status": upstream.get("status"),
            "data": upstream.get("data"),
        }
    raw = upstream.get("data")
    if tool_key in ("history_create", "history_update", "history_delete", "history_end_latest"):
        return shaping.shape_write_receipt(raw)
    if tool_key in ("history_filter", "history_list"):
        limit = 20
        if query and query.get("limit") is not None:
            try:
                limit = max(1, min(50, int(query["limit"])))
            except (TypeError, ValueError):
                pass
        if query and query.get("pageSize") is not None:
            try:
                limit = max(1, min(50, int(query["pageSize"])))
            except (TypeError, ValueError):
                pass
        return {"ok": True, "events": shaping.shape_history_events(raw, limit=limit)}
    if tool_key == "history_options":
        return {"ok": True, "options": shaping.shape_options(raw)}
    if tool_key == "baby_profile":
        return shaping.shape_baby_profile(raw)
    return {"ok": True, "data": raw}


def a_token_dep(x_pangbao_api_token: Optional[str] = Header(None, alias=API_TOKEN_HEADER)) -> Optional[str]:
    """FastAPI Header 依赖。"""
    return x_pangbao_api_token
