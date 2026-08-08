"""
护理留意分析 / 飞轮路由

业务说明：
提供 Go 可内调的 POST /v1/care-alert/analyze 与 POST /v1/care-alert/feedback。
analyze：按传入模型（deepseek / zhipu）执行 KG+LLM，返回可映射 Flutter DTO 的 items。
feedback：固定意图 ACK（ignore|follow_up），无 NLP、不扣 clinic 配额。
Go 转发 feedback 为 best-effort：本接口失败不阻断客户端忽略/追问主路径。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.care_alert.schemas.care_alert import (
    CareAlertAnalyzeRequest,
    CareAlertAnalyzeResponse,
    CareAlertFeedbackRequest,
    CareAlertFeedbackResponse,
    CareAlertItemDto,
)
from app.care_alert.services.analyze import run_care_alert_analyze

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/care-alert", tags=["护理留意"])


@router.post(
    "/analyze",
    response_model=CareAlertAnalyzeResponse,
    response_model_by_alias=True,
    summary="护理留意日分析（Go 内调）",
)
async def care_alert_analyze(request: CareAlertAnalyzeRequest) -> CareAlertAnalyzeResponse:
    """
    护理留意分析接口。

    业务逻辑：
    1. 校验 device_no 与 model
    2. 拉取历史 / 知识 / 画像（可与 Go 透传合并）
    3. 按模型调用 LLM，产出 items 列表

    Returns:
        {"items": [...]}，字段 camelCase 对齐 Flutter CareAlertEventItem
    """
    logger.info(
        "护理留意分析请求: device_no=%s day=%s model=%s",
        request.device_no,
        request.day,
        request.model if isinstance(request.model, str) else getattr(request.model, "provider", "?"),
    )
    try:
        raw_items = await run_care_alert_analyze(request)
    except ValueError as e:
        # 模型参数错误 → 400
        logger.warning("护理留意请求参数错误: %s", e)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("护理留意分析失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="护理留意分析失败") from e

    # dict → DTO，保证响应别名序列化为 Flutter/Go 契约字段
    items = [CareAlertItemDto.model_validate(x) for x in raw_items]
    return CareAlertAnalyzeResponse(items=items)


@router.post(
    "/feedback",
    response_model=CareAlertFeedbackResponse,
    summary="护理留意固定意图飞轮（Go 内调，无 NLP）",
)
async def care_alert_feedback(request: CareAlertFeedbackRequest) -> CareAlertFeedbackResponse:
    """
    固定意图飞轮 ACK。

    业务逻辑：
    1. 校验 intent ∈ {ignore, follow_up}
    2. 落日志供后续质量统计接线；不解析自由文本、不调用 LLM
    3. 返回 ok=true（Go 侧失败亦不阻断客户端）
    """
    # 仅 ACK：尚无 suggestion→知识 doc 映射，故不 invent 质量分 NLP
    logger.info(
        "护理留意飞轮 ACK: device_no=%s suggestion_id=%s intent=%s day=%s",
        request.device_no,
        request.suggestion_id,
        request.intent,
        request.day,
    )
    return CareAlertFeedbackResponse(ok=True)
