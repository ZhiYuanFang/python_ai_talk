"""
护理留意分析 / 飞轮路由

业务说明：
提供 Go 可内调的 POST /v1/care-alert/analyze 与 POST /v1/care-alert/feedback。
analyze：按传入模型执行史+LLM（无通识检索），返回可映射 Flutter DTO 的 items，
并写入 suggestionId→建议快照。
feedback：固定意图 ignore|follow_up，写入本地 ledger 并按阈值重写全局对比样例 prompt；
无 NLP、不扣 clinic 配额、不通识质量分。
Go 转发 feedback 为 best-effort：本接口失败不阻断客户端忽略/追问主路径。
"""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, HTTPException

from app.care_alert.schemas.care_alert import (
    CareAlertAnalyzeRequest,
    CareAlertAnalyzeResponse,
    CareAlertFeedbackRequest,
    CareAlertFeedbackResponse,
    CareAlertItemDto,
)
from app.care_alert.services.analyze import run_care_alert_analyze
from app.care_alert.services.flywheel_store import care_alert_flywheel_store
from app.care_alert.services.prompt_flywheel import record_feedback_and_maybe_rewrite

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
    3. 按模型调用 LLM，产出 items 列表并写建议快照

    Returns:
        {"items": [...]}，字段 camelCase 对齐 Flutter CareAlertEventItem
    """
    logger.info(
        "护理留意分析请求: device_no=%s day=%s model=%s",
        request.device_no,
        request.day,
        (
            "(fallback-only)"
            if request.model is None
            else (
                request.model
                if isinstance(request.model, str)
                else getattr(request.model, "provider", "?")
            )
        ),
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
    固定意图 prompt 飞轮。

    业务逻辑：
    1. 校验 intent ∈ {ignore, follow_up}
    2. 按 suggestion_id 读建议快照
    3. 有快照则写入本地 ledger，并按阈值重写全局对比样例；无快照/失败仅打日志
    4. 始终返回 ok=true（不阻断 Go/客户端）；不通识质量分
    """
    try:
        snapshot = await care_alert_flywheel_store.get_snapshot(request.suggestion_id)
        if not snapshot:
            logger.info(
                "护理留意飞轮无快照: device_no=%s suggestion_id=%s intent=%s",
                request.device_no,
                request.suggestion_id,
                request.intent,
            )
        else:
            entry = {
                "ts": int(time.time()),
                "device_no": request.device_no,
                "suggestion_id": request.suggestion_id,
                "intent": request.intent,
                "day": request.day or snapshot.get("day") or "",
                "event_name": snapshot.get("event_name") or "",
                "event_id": snapshot.get("event_id") or "",
                "reason_type": snapshot.get("reason_type") or "other",
                "score_band": snapshot.get("score_band") or "weak",
                "summary_line": snapshot.get("summary_line") or "",
            }
            record_feedback_and_maybe_rewrite(entry)
            logger.info(
                "护理留意 prompt 飞轮已记: device_no=%s suggestion_id=%s intent=%s type=%s band=%s",
                request.device_no,
                request.suggestion_id,
                request.intent,
                entry["reason_type"],
                entry["score_band"],
            )
    except Exception as e:
        # 飞轮异常不阻断 ACK
        logger.error(
            "护理留意飞轮异常（仍 ACK）: suggestion_id=%s err=%s",
            request.suggestion_id,
            e,
            exc_info=True,
        )

    return CareAlertFeedbackResponse(ok=True)
