"""
FastAPI 应用主入口

业务说明：
本文件是 Python AI 服务的启动入口，负责初始化 FastAPI 应用、加载配置、注册路由。
后台任务仅清理低分意图缓存（feeding_intents）；不再维护通识知识飞轮。
采用延迟初始化 + 后台预热策略，确保服务快速启动并响应健康检查。

设计思路：
1. 使用 FastAPI 创建高性能的异步 Web 服务
2. 配置日志系统，便于调试和监控
3. 注册 API 路由，组织接口结构
4. 支持跨域请求（CORS）
5. 提供优雅的启动和关闭钩子
6. 启动后台定时任务，定期清理低分意图缓存
7. 意图缓存 embedding 在后台预热，不阻塞服务启动
"""

import asyncio
import logging
import os

# 在导入 chromadb 之前设置官方认可的遥测开关（CHROMA_TELEMETRY 无效，勿再依赖）
os.environ["ANONYMIZED_TELEMETRY"] = "False"

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config.settings import settings
from app.shared.http_client import http_client

# 后台任务取消对象
_cleanup_task = None
_warmup_task = None


async def _periodic_cleanup():
    """
    定期清理低分意图缓存

    业务逻辑：
    1. 每隔 24 小时执行一次
    2. 仅清理 feeding_intents 质量分低于 0.3 的条目
    """
    while True:
        try:
            from app.feeding.services.intent_cache_store import intent_cache_store

            logger.info("开始清理低分意图缓存...")
            removed = intent_cache_store.cleanup_low_quality(threshold=0.3)
            logger.info("意图缓存低分清理完成: removed=%s", removed)
        except Exception as e:
            logger.error(f"意图缓存清理失败: {str(e)}", exc_info=True)

        await asyncio.sleep(24 * 60 * 60)


async def _warmup_intent_cache():
    """
    后台预热意图缓存向量存储

    业务逻辑：
    1. 触发 feeding_intents 集合初始化（加载 Embedding）
    2. 可选：启动时清空测脏缓存
    3. 不阻塞服务启动
    """
    try:
        logger.info("开始后台预热意图缓存...")
        from app.feeding.services.intent_cache_store import intent_cache_store

        # 触发懒加载初始化
        _ = intent_cache_store.search("__warmup__", n_results=1)
        logger.info("意图缓存预热完成（feeding_intents）")

        if settings.clear_feeding_intents_on_startup:
            intent_cache_store.reset_collection()
            logger.warning(
                "CLEAR_FEEDING_INTENTS_ON_STARTUP=true，已清空 feeding_intents；"
                "完成后请改回 false，避免每次重启丢掉飞轮"
            )
    except Exception as e:
        logger.error(f"意图缓存后台预热失败: {str(e)}", exc_info=True)


# 配置日志系统
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)


class _HealthCheckAccessFilter(logging.Filter):
    """过滤健康检查路径的 uvicorn access log，避免 Docker healthcheck 刷屏。"""

    def filter(self, record: logging.LogRecord) -> bool:
        return "/v1/health" not in record.getMessage()


logging.getLogger("uvicorn.access").addFilter(_HealthCheckAccessFilter())
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)

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
    app = FastAPI(
        title="Python AI Talk Service",
        description="母婴喂养场景的自然语言意图识别服务",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        """请求体/查询参数校验失败（422）时记录摘要。"""
        errors = exc.errors()[:8]
        logger.warning(
            f"请求校验失败 422: path={request.url.path}, errors={errors}"
        )
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors()},
        )

    @app.on_event("startup")
    async def startup_event():
        """
        应用启动钩子

        业务逻辑：
        1. 记录启动日志
        2. 启动意图缓存后台预热
        3. 启动意图缓存定期清理
        """
        logger.info("Python AI Talk Service 启动中...")

        global _warmup_task
        _warmup_task = asyncio.create_task(_warmup_intent_cache())
        logger.info("意图缓存后台预热任务已启动")

        global _cleanup_task
        _cleanup_task = asyncio.create_task(_periodic_cleanup())
        logger.info("意图缓存清理任务已启动（每 24 小时）")

        logger.info("Python AI Talk Service 启动完成")

    @app.on_event("shutdown")
    async def shutdown_event():
        """应用关闭钩子：取消后台任务并关闭 HTTP 客户端。"""
        logger.info("Python AI Talk Service 关闭中...")

        global _warmup_task
        if _warmup_task:
            _warmup_task.cancel()
            try:
                await _warmup_task
            except asyncio.CancelledError:
                pass
            logger.info("意图缓存预热任务已取消")

        global _cleanup_task
        if _cleanup_task:
            _cleanup_task.cancel()
            try:
                await _cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("意图缓存清理任务已取消")

        await http_client.close()
        logger.info("Python AI Talk Service 关闭完成")

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.server_port,
        workers=4,
        reload=False,
        log_level=settings.log_level.lower(),
    )
