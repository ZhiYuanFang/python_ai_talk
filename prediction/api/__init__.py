"""
python-prediction HTTP API 包

业务说明：
聚合本服务对外路由；骨架阶段仅挂载健康检查。
"""

from fastapi import APIRouter

from prediction.api.routes import health

# 对外 API 总路由，挂到 /v1 前缀
router = APIRouter()
router.include_router(health.router)
