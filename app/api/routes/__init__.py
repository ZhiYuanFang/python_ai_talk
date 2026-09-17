"""
路由汇总模块

业务说明：
汇总所有子路由，创建统一的 APIRouter。
所有接口都挂载在 /v1 前缀下。

包含的子路由：
- /health：健康检查
- /analyze/intent：意图分析
- /clinic：智能陪伴（非流式）
- /clinic/stream：智能陪伴续聊（流式）
- /care-alert/analyze：护理留意日分析（Go 内调）
- /growth-trajectory/turn：成长轨迹预测（SSE，Go 内调）
"""

from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.intent import router as intent_router
from app.api.routes.clinic import router as clinic_router
from app.api.routes.care_alert import router as care_alert_router
from app.api.routes.growth_trajectory import router as growth_trajectory_router

# 创建主路由，统一前缀 /v1
router = APIRouter(prefix="/v1")

# 注册子路由
router.include_router(health_router)
router.include_router(intent_router)
router.include_router(clinic_router)
router.include_router(care_alert_router)
router.include_router(growth_trajectory_router)
