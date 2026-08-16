"""
多 G 门禁：校验 G → 转发内部 OpenClaw

业务说明：
对外入口为本路由；OpenClaw 仍用内部单 token。
A 头原样转发，供插件打 Python tools。
产品写死 Gateway LLM 为 deepseek/deepseek-v4-flash：不转发 x-openclaw-model，
故 Go 注模头暂时无效（Go 仓可仍发送该头）。
"""

from __future__ import annotations

import logging
from typing import Optional

import httpx
from fastapi import APIRouter, Header, HTTPException, Request, Response

from app.agent_console import repository as repo
from app.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent-gate", tags=["agent-gate"])


def _extract_bearer(authorization: Optional[str]) -> str:
    if not authorization:
        return ""
    parts = authorization.split(None, 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return authorization.strip()


@router.api_route("/v1/chat/completions", methods=["POST", "GET", "OPTIONS"])
async def gate_chat_completions(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_pangbao_api_token: Optional[str] = Header(None, alias="x-pangbao-api-token"),
):
    """
    校验 G（Authorization Bearer）后转发 Gateway。

    G 失效/未知 → 401；通过后用 internal_gateway_token。
    不转发 x-openclaw-model（LLM 由 openclaw.json5 钉死 flash）。
    """
    if request.method == "OPTIONS":
        return Response(status_code=204)

    g = _extract_bearer(authorization)
    if not g:
        raise HTTPException(status_code=401, detail="缺少 Gateway Token（Authorization Bearer）")

    try:
        pair = repo.find_pair_by_g_hash(g)
    except Exception as e:
        logger.error("门禁查库失败: %s", e)
        raise HTTPException(status_code=503, detail="租户注册表不可用") from e

    if not pair:
        raise HTTPException(status_code=401, detail="Gateway Token 无效")
    if pair.get("g_enabled") is False:
        raise HTTPException(status_code=401, detail="Gateway Token 已失效，无法使用智能体")

    base = (settings.internal_gateway_url or "").rstrip("/")
    token = (settings.internal_gateway_token or "").strip()
    if not base or not token:
        raise HTTPException(status_code=503, detail="内部 Gateway 未配置")

    body = await request.body()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": request.headers.get("content-type") or "application/json",
        "Accept": request.headers.get("accept") or "application/json",
    }
    # 透传会话与 A Token；故意不转发 x-openclaw-model（忽略 Go 注模）
    for name in (
        "x-openclaw-session-key",
        "x-pangbao-api-token",
    ):
        v = request.headers.get(name)
        if v:
            headers[name] = v
    if x_pangbao_api_token and "x-pangbao-api-token" not in headers:
        headers["x-pangbao-api-token"] = x_pangbao_api_token

    url = f"{base}/v1/chat/completions"
    try:
        logger.info(f"请求url: {url}")
        logger.info(f"请求头: {headers}")
        async with httpx.AsyncClient(timeout=120.0) as client:
            upstream = await client.request(
                request.method,
                url,
                content=body,
                headers=headers,
            )
    except Exception as e:
        logger.error("转发 Gateway 失败: %s", e)
        raise HTTPException(status_code=502, detail=f"Gateway 不可达: {e}") from e

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type"),
    )


@router.get("/health")
async def gate_health():
    """门禁存活。"""
    return {"ok": True, "gateway": bool(settings.internal_gateway_url)}
