"""
路由汇总模块

业务说明：
汇总所有子路由，创建统一的 APIRouter。
所有接口都挂载在 /v1 前缀下。

包含的子路由：
- /health：健康检查
- /analyze/intent：意图分析
- /clinic/stream：智能陪伴续聊（流式；与 tip 共享 device_no 会话）
- /tip/stream：事件开场陪伴（流式；写入共享会话，可供 clinic 续聊）
- /care-alert/analyze：护理留意日分析（Go 内调）
- /care-alert/feedback：护理留意固定意图飞轮 ACK（Go 内调，无 NLP）
- /knowledge：知识库管理（上传、列表、详情、更新、删除、统计、分类）
"""

from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.intent import router as intent_router
from app.api.routes.clinic import router as clinic_router
from app.api.routes.tip import router as tip_router
from app.api.routes.care_alert import router as care_alert_router
from app.api.routes.knowledge import router as knowledge_router

# 创建主路由，统一前缀 /v1
router = APIRouter(prefix="/v1")

# 注册子路由
router.include_router(health_router)
router.include_router(intent_router)
router.include_router(clinic_router)
router.include_router(tip_router)
router.include_router(care_alert_router)
router.include_router(knowledge_router)
