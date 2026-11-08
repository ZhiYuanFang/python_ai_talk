"""
健康检查路由（python-prediction）

业务说明：
提供 /v1/health，供 Docker healthcheck 与编排探活使用。
响应中的 service 字段必须标识为 python-prediction，避免与 talk 混淆。
"""

from fastapi import APIRouter

# 健康检查路由实例
router = APIRouter(tags=["健康检查"])


@router.get("/health", summary="健康检查")
async def health_check():
    """
    健康检查接口

    业务逻辑：
    返回服务状态，供 Docker 与负载均衡器判断本进程是否可用。

    Returns:
        含 status / version / service 的健康检查响应
    """
    return {
        "status": "healthy",
        "version": "0.1.0",
        "service": "python-prediction",
    }
