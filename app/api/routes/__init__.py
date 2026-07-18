"""
路由汇总模块

业务说明：
汇总所有子路由，创建统一的 APIRouter。
所有接口都挂载在 /v1 前缀下。

包含的子路由：
- /health：健康检查
- /analyze/intent：意图分析
- /clinic/stream：胖宝诊疗（流式）
- /tip/stream：小贴士生成（流式）
"""

from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.intent import router as intent_router
from app.api.routes.clinic import router as clinic_router
from app.api.routes.tip import router as tip_router

# 创建主路由，统一前缀 /v1
router = APIRouter(prefix="/v1")

# 注册子路由
router.include_router(health_router)
router.include_router(intent_router)
router.include_router(clinic_router)
router.include_router(tip_router)
