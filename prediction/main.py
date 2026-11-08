"""
python-prediction FastAPI 入口

业务说明：
预测机器学习模型微服务的启动入口。本阶段仅注册健康检查路由，
默认监听 8001，与 python-ai-talk（8000）端口隔离。
模型推理等业务 API 由后续变更接入，本文件不预埋假接口。
"""

import logging

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from prediction.api import router as api_router

# 本服务日志：与 talk 进程分离，便于容器日志排查
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("python-prediction")

# 创建 FastAPI 应用；title 用于 OpenAPI 文档标识服务名
app = FastAPI(
    title="python-prediction",
    description="预测机器学习模型服务（骨架阶段仅健康检查）",
    version="0.1.0",
)

# 允许跨域，便于本地联调；生产可由网关统一约束
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载 /v1 业务前缀（当前仅 /v1/health）
app.include_router(api_router, prefix="/v1")


@app.on_event("startup")
async def on_startup():
    """
    启动钩子

    业务逻辑：
    记录服务启动日志，确认骨架进程已就绪。后续可在此加载模型权重。
    """
    logger.info("python-prediction 已启动（骨架模式，无模型推理）")


if __name__ == "__main__":
    # 本地直接 python -m / 本文件启动时使用 8001，与 Docker CMD 一致
    uvicorn.run(
        "prediction.main:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
    )
