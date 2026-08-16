"""
路由汇总模块

业务说明：
汇总子路由，统一挂载在 /v1。
Intent / Clinic / Care 产品编排已迁 OpenClaw Gateway；本进程仅健康检查、飞轮/出卡 tools、知识库。
"""

from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.knowledge import router as knowledge_router
from app.api.routes.openclaw_tools import router as openclaw_tools_router

router = APIRouter(prefix="/v1")

router.include_router(health_router)
router.include_router(openclaw_tools_router)
router.include_router(knowledge_router)
