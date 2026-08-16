"""
智能体管理后台 API + 页面

业务说明：
主页仅 G/A Token 进入 API 管理；右上管理员账密。
浅空蓝主题，品牌「AI喂养智能体」。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from itsdangerous import BadSignature, URLSafeSerializer
from pydantic import BaseModel, Field

from app.agent_console import repository as repo
from app.agent_console.catalog import TOOL_CATALOG
from app.config.settings import settings

router = APIRouter(tags=["agent-console"])

_STATIC = Path(__file__).resolve().parent.parent.parent / "agent_console" / "static"


def _ser() -> URLSafeSerializer:
    return URLSafeSerializer(settings.console_secret_key, salt="agent-console")


def _set_cookie(resp: Response, name: str, payload: dict) -> None:
    resp.set_cookie(
        name,
        _ser().dumps(payload),
        httponly=True,
        samesite="lax",
        max_age=86400 * 7,
    )


def _read_cookie(request: Request, name: str) -> Optional[dict]:
    raw = request.cookies.get(name)
    if not raw:
        return None
    try:
        data = _ser().loads(raw)
        return data if isinstance(data, dict) else None
    except BadSignature:
        return None


class TokenLoginReq(BaseModel):
    token: str = Field(..., min_length=8)


class AdminLoginReq(BaseModel):
    username: str
    password: str


class IssuePairReq(BaseModel):
    display_name: str = Field(..., min_length=1)


class SetGEnabledReq(BaseModel):
    pair_id: int
    enabled: bool


class SaveEndpointReq(BaseModel):
    tool_key: str
    url: str
    method: str = "POST"
    upstream_auth: str = ""


@router.get("/console", response_class=HTMLResponse)
@router.get("/console/", response_class=HTMLResponse)
async def console_home():
    """主页 HTML。"""
    path = _STATIC / "index.html"
    return HTMLResponse(path.read_text(encoding="utf-8"))


@router.get("/console/app.js")
async def console_js():
    path = _STATIC / "app.js"
    return Response(path.read_text(encoding="utf-8"), media_type="application/javascript")


@router.get("/console/styles.css")
async def console_css():
    path = _STATIC / "styles.css"
    return Response(path.read_text(encoding="utf-8"), media_type="text/css")


@router.get("/console/vendor/marked.min.js")
async def console_marked_js():
    """控制台 guide Markdown 渲染（vendored marked，离线可用）。"""
    path = _STATIC / "vendor" / "marked.min.js"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="marked.min.js 缺失")
    return Response(path.read_text(encoding="utf-8"), media_type="application/javascript")


@router.post("/console/api/tenant/login")
async def tenant_login(req: TokenLoginReq, response: Response):
    """G 或 A 进入配置会话。"""
    try:
        pair = repo.find_pair_by_token(req.token.strip())
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"数据库不可用: {e}") from e
    if not pair:
        raise HTTPException(status_code=401, detail="Token 无效")
    _set_cookie(response, "agent_tenant", {"pair_id": pair["id"]})
    return {
        "ok": True,
        "display_name": pair["display_name"],
        "g_token": pair["g_token"],
        "a_token": pair["a_token"],
        "g_enabled": pair["g_enabled"],
        "a_enabled": pair["a_enabled"],
    }


@router.get("/console/api/tenant/me")
async def tenant_me(request: Request):
    sess = _read_cookie(request, "agent_tenant")
    if not sess:
        raise HTTPException(status_code=401, detail="未登录")
    pairs = {p["id"]: p for p in repo.list_pairs()}
    pair = pairs.get(int(sess["pair_id"]))
    if not pair:
        raise HTTPException(status_code=401, detail="租户不存在")
    endpoints = repo.list_endpoints(int(pair["id"]))
    return {
        "ok": True,
        "pair": pair,
        "endpoints": endpoints,
        "catalog": TOOL_CATALOG,
        "guide": _go_guide_markdown(),
    }


@router.post("/console/api/tenant/endpoints")
async def tenant_save_endpoint(req: SaveEndpointReq, request: Request):
    sess = _read_cookie(request, "agent_tenant")
    if not sess:
        raise HTTPException(status_code=401, detail="未登录")
    try:
        repo.upsert_endpoint(
            int(sess["pair_id"]),
            req.tool_key,
            req.url,
            method=req.method,
            upstream_auth=req.upstream_auth,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True}


@router.post("/console/api/admin/login")
async def admin_login(req: AdminLoginReq, response: Response):
    try:
        ok = repo.verify_admin(req.username, req.password)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"数据库不可用: {e}") from e
    if not ok:
        raise HTTPException(status_code=401, detail="管理员账密错误")
    _set_cookie(response, "agent_admin", {"u": req.username.strip()})
    return {"ok": True}


def _require_admin(request: Request) -> None:
    if not _read_cookie(request, "agent_admin"):
        raise HTTPException(status_code=401, detail="需要管理员登录")


@router.get("/console/api/admin/pairs")
async def admin_list_pairs(request: Request):
    _require_admin(request)
    return {"ok": True, "pairs": repo.list_pairs()}


@router.post("/console/api/admin/issue")
async def admin_issue(req: IssuePairReq, request: Request):
    _require_admin(request)
    pair = repo.create_pair(req.display_name)
    return {"ok": True, "pair": pair}


@router.post("/console/api/admin/g_enabled")
async def admin_g_enabled(req: SetGEnabledReq, request: Request):
    _require_admin(request)
    ok = repo.set_g_enabled(req.pair_id, req.enabled)
    if not ok:
        raise HTTPException(status_code=404, detail="pair 不存在")
    return {"ok": True}


def _go_guide_markdown() -> str:
    """Go/业务壳接入说明（用户可见）。"""
    gate = "/agent-gate/v1/chat/completions"
    return f"""## 从 Go / 业务壳接入智能体

1. **Gateway Token（G）**：放在 `Authorization: Bearer <G>`，调用本平台**门禁** `{gate}`（不要直连裸 OpenClaw，除非内网调试）。
2. **API Token（A）**：放在独立头 `x-pangbao-api-token: <A>`，供 Agent tools 落库/读史路由。
3. 另需：`x-openclaw-model`、`x-openclaw-session-key`（如 `intent:{{deviceNo}}`）。
4. **G 失效** → 无法使用智能体。**缺 A / 未配 URL** → 对话可能到达，但 history CRUD/读史 tools 失败。
5. 在下方为每个 tool 填写**完整 URL（含域名）**；本页契约说明入参出参；Python **无**默认胖宝 Go 地址。

### 上游 URL（tools → Go history）

推荐 BASE：`http://<Go主机>:9701`（主网关，无 App JWT）或 `http://history-service:9801`（直连）。**不要**用 gateway-app `:9702`。现网 history 的「上游 Bearer」**留空**（勿填用户日更 JWT）。

| tool | Method | path |
|------|--------|------|
| history_create | POST | /device/history/api/event/add |
| history_update | POST | /device/history/api/event/update |
| history_delete | POST | /device/history/api/event/delete |
| history_end_latest | POST | /device/history/api/event/end-latest |
| history_filter | GET | /device/history/api/filter |
| history_list | GET | /device/history/api/list |
| history_options | GET | /device/history/api/event/options |
| baby_profile | GET | /device/history/api/birthday |

环境变量示例：
```
OPENCLAW_GATEWAY_URL=https://<your-host>/agent-gate
OPENCLAW_GATEWAY_TOKEN=<G>
PANGBAO_API_TOKEN=<A>
```
"""
