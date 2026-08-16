"""
Gateway 可调用的业务 / 飞轮 / History HTTP tools

业务说明：
History 读写经本模块按 A Token 查租户 URL 并塑形；飞轮与 Care 出卡仍本机。
请求头 x-pangbao-api-token 必填（history 类）。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.agent_console.history_tools import a_token_dep, run_tool
from app.shared.flywheel_facade import flywheel
from app.shared.suggestion_acceptance import judge_suggestion_acceptance

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tools", tags=["openclaw-tools"])


class FlywheelIntentRetrieveReq(BaseModel):
    query: str = Field(..., description="用户说法")
    n_results: int = Field(1, ge=1, le=5)


class FlywheelIntentRecordReq(BaseModel):
    document: str
    payload: Dict[str, Any] = Field(default_factory=dict)


class FlywheelClinicRecordReq(BaseModel):
    standalone_question: Optional[str] = None
    answer: Optional[str] = None
    age_band: Optional[str] = None


class ClinicJudgeReq(BaseModel):
    user_text: str
    suggestion_text: str
    model_config_payload: Optional[Dict[str, Any]] = Field(
        default=None, alias="model_config"
    )
    model_config = {"populate_by_name": True}


class EmitCareCardsReq(BaseModel):
    device_no: str = ""
    day: str = ""
    items: List[Dict[str, Any]] = Field(default_factory=list)


class EmitCareCardsRes(BaseModel):
    ok: bool = True
    items: List[Dict[str, Any]] = Field(default_factory=list)


class HistoryWriteReq(BaseModel):
    """写史通用体（字段透传上游）。"""

    model_config = {"extra": "allow"}


@router.post("/flywheel/intent/retrieve")
async def tool_flywheel_intent_retrieve(req: FlywheelIntentRetrieveReq) -> Dict[str, Any]:
    hits = flywheel.retrieve_intent(req.query, n_results=req.n_results)
    return {"hits": hits}


@router.post("/flywheel/intent/record")
async def tool_flywheel_intent_record(req: FlywheelIntentRecordReq) -> Dict[str, Any]:
    vid = flywheel.record_intent_outcome(req.document, req.payload)
    return {"id": vid or "", "ok": bool(vid)}


@router.post("/flywheel/clinic/record")
async def tool_flywheel_clinic_record(req: FlywheelClinicRecordReq) -> Dict[str, Any]:
    qa_id = flywheel.record_clinic_accepted_qa(
        standalone_question=req.standalone_question,
        answer=req.answer,
        age_band=req.age_band,
    )
    return {"id": qa_id or "", "ok": bool(qa_id)}


@router.post("/flywheel/clinic/retrieve")
async def tool_flywheel_clinic_retrieve(req: FlywheelIntentRetrieveReq) -> Dict[str, Any]:
    """Clinic 飞轮检索占位（完整捷径仍可由 Gateway 其它路径扩展）。"""
    return {"hits": [], "ok": True, "query": req.query, "n_results": req.n_results}


@router.post("/clinic/judge_implicit_acceptance")
async def tool_clinic_judge(req: ClinicJudgeReq) -> Dict[str, Any]:
    status = await judge_suggestion_acceptance(
        user_text=req.user_text,
        suggestion_text=req.suggestion_text,
        model_config=req.model_config_payload or {},
    )
    return {
        "status": status.value if status is not None else None,
        "ok": status is not None,
    }


@router.post("/care/emit_cards", response_model=EmitCareCardsRes)
async def tool_emit_care_cards(req: EmitCareCardsReq) -> EmitCareCardsRes:
    items = [it for it in (req.items or []) if isinstance(it, dict)]
    return EmitCareCardsRes(ok=True, items=items)


# —— History：按 A 路由 + 塑形 ——


@router.post("/history/create")
async def tool_history_create(
    body: Dict[str, Any],
    a_token: Optional[str] = Depends(a_token_dep),
) -> Dict[str, Any]:
    return await run_tool("history_create", a_token=a_token, json_body=body)


@router.post("/history/update")
async def tool_history_update(
    body: Dict[str, Any],
    a_token: Optional[str] = Depends(a_token_dep),
) -> Dict[str, Any]:
    return await run_tool("history_update", a_token=a_token, json_body=body)


@router.post("/history/delete")
async def tool_history_delete(
    body: Dict[str, Any],
    a_token: Optional[str] = Depends(a_token_dep),
) -> Dict[str, Any]:
    return await run_tool("history_delete", a_token=a_token, json_body=body)


@router.post("/history/end_latest")
async def tool_history_end_latest(
    body: Dict[str, Any],
    a_token: Optional[str] = Depends(a_token_dep),
) -> Dict[str, Any]:
    return await run_tool("history_end_latest", a_token=a_token, json_body=body)


@router.post("/history/filter")
async def tool_history_filter(
    body: Dict[str, Any],
    a_token: Optional[str] = Depends(a_token_dep),
) -> Dict[str, Any]:
    # 插件用 POST 传参，避免复杂 query；也兼容 GET 风格字段
    return await run_tool("history_filter", a_token=a_token, query=body)


@router.post("/history/list")
async def tool_history_list(
    body: Dict[str, Any],
    a_token: Optional[str] = Depends(a_token_dep),
) -> Dict[str, Any]:
    return await run_tool("history_list", a_token=a_token, query=body)


@router.post("/history/options")
async def tool_history_options(
    body: Optional[Dict[str, Any]] = None,
    a_token: Optional[str] = Depends(a_token_dep),
) -> Dict[str, Any]:
    return await run_tool("history_options", a_token=a_token, query=body or {})


@router.post("/baby/profile")
async def tool_baby_profile(
    body: Dict[str, Any],
    a_token: Optional[str] = Depends(a_token_dep),
) -> Dict[str, Any]:
    return await run_tool("baby_profile", a_token=a_token, query=body)
