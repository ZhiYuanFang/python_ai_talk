"""
成长轨迹预测路由

业务说明：
Go 内调 POST /v1/growth-trajectory/turn（SSE）。
事件类型：thinking / question / result / error / done。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.growth_trajectory.schemas.growth_trajectory import GrowthTrajectoryTurnRequest
from app.growth_trajectory.services.turn import iter_growth_trajectory_sse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/growth-trajectory", tags=["成长轨迹"])


@router.post("/turn", summary="成长轨迹预测 turn（SSE）")
async def growth_trajectory_turn(request: GrowthTrajectoryTurnRequest):
    """
    成长轨迹多轮 turn。

    action=start|restart 启动会话；answer 用 Command(resume) 恢复 interrupt。
    """
    logger.info(
        "成长轨迹 turn 请求: device_no=%s action=%s session_id=%s",
        request.device_no,
        request.action,
        request.session_id,
    )
    request.model = {
        "provider": "deepseek",
        "name": "deepseek-v4-flash",
        "max_in_flight": 50,
    }

    # 打印日志
    logger.info("成长轨迹预测请求固定模型为: model=%s", request.model)
    return StreamingResponse(
        iter_growth_trajectory_sse(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
