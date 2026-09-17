"""
护理留意分析路由

业务说明：
提供 Go 可内调的 POST /v1/care-alert/analyze 与 /analyze/stream。
analyze：按传入模型执行史+LLM（无通识检索、无 feedback 飞轮），返回可映射 Flutter DTO 的 items。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.care_alert.schemas.care_alert import (
    CareAlertAnalyzeRequest,
    CareAlertAnalyzeResponse,
    CareAlertItemDto,
)
from app.care_alert.services.analyze import (
    iter_care_alert_analyze_sse,
    run_care_alert_analyze,
)

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
    2. 拉取历史 / 画像（可与 Go 透传历史合并；不通识检索）
    3. 按模型调用 LLM，产出 items 列表

    Returns:
        {"items": [...]}，字段 camelCase 对齐 Flutter CareAlertEventItem
    """
    logger.info(
        "护理留意分析请求: device_no=%s day=%s model=%s",
        request.device_no,
        request.day,
        (
            request.model
            if isinstance(request.model, str)
            else getattr(request.model, "provider", "?")
        ),
    )
    logger.info("护理留意分析请求固定模型为: model=%s", request.model)

    try:
        raw_items = await run_care_alert_analyze(request)
    except ValueError as e:
        logger.warning("护理留意请求参数错误: %s", e)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("护理留意分析失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="护理留意分析失败") from e

    items = [CareAlertItemDto.model_validate(x) for x in raw_items]
    return CareAlertAnalyzeResponse(items=items)


@router.post("/analyze/stream", summary="护理留意日分析（SSE thinking + result）")
async def care_alert_analyze_stream(request: CareAlertAnalyzeRequest):
    """
    流式分析：推送 thinking 增量，终态 result 含 items。
    供 Go 代理至设备侧 /device/api/care-alert/daily/stream。
    """
    request.model = {
        "provider": "deepseek",
        "name": "deepseek-v4-flash",
        "max_in_flight": 50,
    }
    logger.info(
        "护理留意 SSE 分析请求: device_no=%s day=%s model=%s",
        request.device_no,
        request.day,
        (
            request.model
            if isinstance(request.model, str)
            else getattr(request.model, "name", request.model)
        ),
    )
    return StreamingResponse(
        iter_care_alert_analyze_sse(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
