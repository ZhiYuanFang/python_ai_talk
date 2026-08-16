"""
Gateway 可调用的业务 / 飞轮 HTTP tools

业务说明：
OpenClaw Gateway agent 经 HTTP 调用本模块；Go 不经此路径写飞轮。
History 四写优先由 Gateway 直打 Go REST；此处提供飞轮与 Care 出卡、Clinic 隐式判定。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.shared.flywheel_facade import flywheel
from app.shared.suggestion_acceptance import judge_suggestion_acceptance

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tools", tags=["openclaw-tools"])


class FlywheelIntentRetrieveReq(BaseModel):
    """Intent 飞轮检索请求。"""

    query: str = Field(..., description="用户说法")
    n_results: int = Field(1, ge=1, le=5)


class FlywheelIntentRecordReq(BaseModel):
    """Intent 飞轮写入请求（可移植载荷，无跨租户 event_id）。"""

    document: str
    payload: Dict[str, Any] = Field(default_factory=dict)


class FlywheelClinicRecordReq(BaseModel):
    """Clinic 隐式采纳后写入 Q&A 飞轮。"""

    standalone_question: Optional[str] = None
    answer: Optional[str] = None
    age_band: Optional[str] = None


class ClinicJudgeReq(BaseModel):
    """Clinic 隐式采纳判定（供 Gateway Clinic agent 调用）。"""

    user_text: str
    suggestion_text: str
    model_config_payload: Optional[Dict[str, Any]] = Field(
        default=None, alias="model_config"
    )

    model_config = {"populate_by_name": True}


class EmitCareCardsReq(BaseModel):
    """Care Alert 结构化出卡（权威卡片列表）。"""

    device_no: str = ""
    day: str = ""
    items: List[Dict[str, Any]] = Field(default_factory=list)


class EmitCareCardsRes(BaseModel):
    """出卡 tool 响应：Go 从此结构取 items。"""

    ok: bool = True
    items: List[Dict[str, Any]] = Field(default_factory=list)


@router.post("/flywheel/intent/retrieve")
async def tool_flywheel_intent_retrieve(req: FlywheelIntentRetrieveReq) -> Dict[str, Any]:
    """Gateway Intent：检索意图飞轮仓。"""
    hits = flywheel.retrieve_intent(req.query, n_results=req.n_results)
    return {"hits": hits}


@router.post("/flywheel/intent/record")
async def tool_flywheel_intent_record(req: FlywheelIntentRecordReq) -> Dict[str, Any]:
    """Gateway Intent：写入意图飞轮（可移植）。"""
    vid = flywheel.record_intent_outcome(req.document, req.payload)
    return {"id": vid or "", "ok": bool(vid)}


@router.post("/flywheel/clinic/record")
async def tool_flywheel_clinic_record(req: FlywheelClinicRecordReq) -> Dict[str, Any]:
    """Gateway Clinic：隐式采纳后写 Clinic 飞轮。"""
    qa_id = flywheel.record_clinic_accepted_qa(
        standalone_question=req.standalone_question,
        answer=req.answer,
        age_band=req.age_band,
    )
    return {"id": qa_id or "", "ok": bool(qa_id)}


@router.post("/clinic/judge_implicit_acceptance")
async def tool_clinic_judge(req: ClinicJudgeReq) -> Dict[str, Any]:
    """
    Gateway Clinic：判定本轮用户话是否隐式采纳上轮建议。

    不经 Go；返回 status 字符串供 agent 决定是否调 clinic record。
    """
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
    """
    Gateway Care Alert：结构化出卡 tool。

    业务逻辑：校验并原样回传 items，作为卡片权威结果（无飞轮副作用）。
    """
    items = [it for it in (req.items or []) if isinstance(it, dict)]
    logger.info(
        "emit_care_cards: device_no=%s day=%s n=%s",
        req.device_no,
        req.day,
        len(items),
    )
    return EmitCareCardsRes(ok=True, items=items)
