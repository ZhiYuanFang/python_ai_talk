"""
健康检查路由

业务说明：
提供 /v1/health 接口，用于 Docker healthcheck 和负载均衡器的健康检查。
返回服务状态和版本信息。
"""

from fastapi import APIRouter

# 创建路由实例
router = APIRouter(tags=["健康检查"])


@router.get("/health", summary="健康检查")
async def health_check():
    """
    健康检查接口

    业务逻辑：
    返回服务状态信息，供 Docker 和负载均衡器检测服务可用性。

    Returns:
        健康检查响应，包含状态和版本
    """
    return {
        "status": "healthy",
        "version": "0.1.0",
        "service": "python-ai-talk",
    }
