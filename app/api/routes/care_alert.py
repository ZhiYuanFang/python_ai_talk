"""
护理留意分析 / 飞轮路由

业务说明：
提供 Go 可内调的 POST /v1/care-alert/analyze 与 POST /v1/care-alert/feedback。
analyze：按传入模型（deepseek / zhipu）执行 KG+LLM，返回可映射 Flutter DTO 的 items，
并写入 suggestionId→knowledge_ids 飞轮映射。
feedback：固定意图 ignore|follow_up，对映射通识文档更新质量分；无 NLP、不扣 clinic 配额。
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
from app.care_alert.services.flywheel_store import care_alert_flywheel_store

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
    2. 拉取历史 / 合格通识 / 画像（可与 Go 透传历史合并；不通识硬塞）
    3. 按模型调用 LLM，产出 items 列表并写飞轮映射

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
    固定意图通识飞轮。

    业务逻辑：
    1. 校验 intent ∈ {ignore, follow_up}
    2. 按 suggestion_id 读映射 knowledge_ids
    3. follow_up → +1、ignore → -1 更新通识质量分；无映射/失败仅打日志
    4. 始终返回 ok=true（不阻断 Go/客户端）
    """
    feedback = 1 if request.intent == "follow_up" else -1
    try:
        knowledge_ids = await care_alert_flywheel_store.get_knowledge_ids(
            request.suggestion_id
        )
        if not knowledge_ids:
            logger.info(
                "护理留意飞轮无映射或空 ids: device_no=%s suggestion_id=%s intent=%s",
                request.device_no,
                request.suggestion_id,
                request.intent,
            )
        else:
            from app.shared.vector_store import vector_store

            for kid in knowledge_ids:
                try:
                    vector_store.update_quality_score(str(kid), feedback)
                except Exception as e:
                    logger.warning(
                        "护理留意通识质量更新失败 id=%s: %s", kid, e
                    )
            logger.info(
                "护理留意飞轮完成: device_no=%s suggestion_id=%s intent=%s kids=%s",
                request.device_no,
                request.suggestion_id,
                request.intent,
                len(knowledge_ids),
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
