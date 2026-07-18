"""
FastAPI 应用主入口

业务说明：
本文件是 Python AI 服务的启动入口，负责初始化 FastAPI 应用、加载配置、注册路由。

设计思路：
1. 使用 FastAPI 创建高性能的异步 Web 服务
2. 配置日志系统，便于调试和监控
3. 注册 API 路由，组织接口结构
4. 支持跨域请求（CORS）
5. 提供优雅的启动和关闭钩子
"""

import logging
import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config.settings import settings
from app.services.http_client import http_client
from app.services.vector_store import vector_store

# 配置日志系统
# 设置日志级别（DEBUG < INFO < WARNING < ERROR < CRITICAL）
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # 输出到控制台
    ],
)

# 初始化日志记录器
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    创建 FastAPI 应用实例

    业务逻辑：
    1. 创建 FastAPI 应用实例，配置基本信息
    2. 添加 CORS 中间件，支持跨域请求
    3. 注册 API 路由
    4. 添加启动和关闭钩子

    Returns:
        FastAPI 应用实例
    """
    # 创建 FastAPI 应用实例
    app = FastAPI(
        title="Python AI Talk Service",  # 应用名称
        description="母婴喂养场景的自然语言意图识别服务",  # 应用描述
        version="0.1.0",  # 应用版本
        docs_url="/docs",  # Swagger UI 文档地址
        redoc_url="/redoc",  # ReDoc 文档地址
    )

    # 添加 CORS 中间件
    # 允许跨域请求，方便前端或其他服务调用
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 允许所有来源（生产环境应限制具体域名）
        allow_credentials=True,  # 允许携带凭证
        allow_methods=["*"],  # 允许所有 HTTP 方法
        allow_headers=["*"],  # 允许所有请求头
    )

    # 注册 API 路由
    # 将路由模块中的所有接口注册到应用中
    app.include_router(router)

    # 添加启动钩子
    # 在应用启动前执行初始化操作
    @app.on_event("startup")
    async def startup_event():
        """
        应用启动钩子

        业务逻辑：
        1. 记录启动日志
        2. 初始化向量存储服务（加载模型）
        3. 检查并构建向量库（如果为空）
        """
        logger.info("Python AI Talk Service 启动中...")

        # 初始化向量存储服务
        # 这会加载 BGE-small-zh-v1.5 模型并初始化 Chroma 客户端
        # 如果是第一次启动，可能需要下载模型（约 90MB）
        logger.info("初始化向量存储服务...")
        _ = vector_store

        # 检查向量库是否为空，如果为空则尝试构建
        doc_count = vector_store.get_document_count()
        if doc_count == 0:
            logger.warning("向量库为空，尝试自动构建...")
            try:
                # 尝试从知识库目录加载文档并构建向量库
                from scripts.build_vector_db import build_vector_db
                # 修复: build_vector_db 是同步函数，不能用 await
                build_vector_db()
                logger.info("向量库构建完成")
            except Exception as e:
                # 修复: 用 error 级别 + exc_info 记录完整 traceback，避免静默失败
                logger.error(f"向量库自动构建失败: {str(e)}", exc_info=True)

        logger.info("Python AI Talk Service 启动完成")

    # 添加关闭钩子
    # 在应用关闭前执行清理操作
    @app.on_event("shutdown")
    async def shutdown_event():
        """
        应用关闭钩子

        业务逻辑：
        1. 关闭 HTTP 客户端连接
        2. 记录关闭日志
        """
        logger.info("Python AI Talk Service 关闭中...")

        # 关闭 HTTP 客户端连接
        await http_client.close()

        logger.info("Python AI Talk Service 关闭完成")

    return app


# 创建 FastAPI 应用实例
app = create_app()


if __name__ == "__main__":
    """
    应用入口

    业务逻辑：
    1. 使用 uvicorn 启动 FastAPI 应用
    2. 配置监听地址和端口
    3. 配置工作进程数
    """
    # 使用 uvicorn 启动应用
    # uvicorn 是一个高性能的 ASGI 服务器，专门用于运行 FastAPI 等异步 Web 框架
    uvicorn.run(
        "app.main:app",  # 应用模块路径
        host="0.0.0.0",  # 监听所有网络接口
        port=settings.server_port,  # 服务端口
        workers=4,  # 工作进程数（生产环境可根据 CPU 核心数调整）
        reload=True,  # 开发环境自动重载（生产环境应关闭）
        log_level=settings.log_level.lower(),  # 日志级别
    )