"""
按完整 URL 调用租户上游

业务说明：
不再使用环境默认 Go 基址；无 URL 则失败。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import httpx

logger = logging.getLogger(__name__)


async def call_upstream(
    method: str,
    url: str,
    *,
    json_body: Any = None,
    query: Optional[Dict[str, Any]] = None,
    bearer: str = "",
    timeout: float = 30.0,
) -> Dict[str, Any]:
    """
    调用租户配置的完整 URL。

    Returns:
        {ok, status, data}；网络/HTTP 错误 ok=False
    """
    if not (url or "").strip():
        return {"ok": False, "status": 0, "error": "未配置该 tool 的完整 URL", "data": None}

    final_url = url.strip()
    if query:
        q = {k: v for k, v in query.items() if v is not None and v != ""}
        if q:
            sep = "&" if "?" in final_url else "?"
            final_url = f"{final_url}{sep}{urlencode(q, doseq=True)}"

    headers = {"Accept": "application/json"}
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    if json_body is not None:
        headers["Content-Type"] = "application/json"

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.request(
                method.upper(),
                final_url,
                json=json_body if json_body is not None else None,
                headers=headers,
            )
        text = resp.text
        data: Any = text
        try:
            data = resp.json() if text else None
        except Exception:
            pass
        if resp.status_code >= 400:
            return {"ok": False, "status": resp.status_code, "error": "上游 HTTP 错误", "data": data}
        return {"ok": True, "status": resp.status_code, "data": data}
    except Exception as e:
        logger.warning("上游调用失败 url=%s err=%s", final_url, e)
        return {"ok": False, "status": 0, "error": str(e), "data": None}
