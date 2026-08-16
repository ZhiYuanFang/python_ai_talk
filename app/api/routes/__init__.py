"""
路由汇总模块

业务说明：
汇总 /v1 tools、知识库、健康检查；另挂门禁与控制台（无 /v1 前缀）。
"""

from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.knowledge import router as knowledge_router
from app.api.routes.openclaw_tools import router as openclaw_tools_router

router = APIRouter(prefix="/v1")

router.include_router(health_router)
router.include_router(openclaw_tools_router)
router.include_router(knowledge_router)
