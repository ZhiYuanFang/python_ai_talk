"""
路由汇总模块

业务说明：
汇总所有子路由，创建统一的 APIRouter。
所有接口都挂载在 /v1 前缀下。

包含的子路由：
- /health：健康检查
- /analyze/intent：意图分析
- /admin/intent-cache：事件短说法向量管理（Hub）
- /admin/type-cache：类型关键字向量管理（Hub，遗留）
- /admin/op-cache：OP 轨整段飞轮管理（Hub）
- /admin/read-source-cache：R·source 整段飞轮管理（Hub）
- /admin/qty-cache：数量整段飞轮管理（Hub）
- /admin/remark-cache：备注整段飞轮管理（Hub）
- /admin/time-cache：时间相对配方飞轮管理（Hub）
- /admin/predict-cache：预测两维整段飞轮管理（Hub）
- /admin/locate-cache：U/D 定位策略飞轮管理（Hub）
- /admin/history-speak-cache：查史播报整段飞轮管理（Hub）
- /admin/rule-gaps：规则缺口收件箱（Hub）
- /clinic：智能陪伴（非流式）
- /clinic/stream：智能陪伴续聊（流式）
- /care-alert/analyze：护理留意日分析（Go 内调）
- /growth-trajectory/turn：成长轨迹预测（SSE，Go 内调）
"""

from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.intent import router as intent_router
from app.api.routes.intent_cache_admin import router as intent_cache_admin_router
from app.api.routes.type_cache_admin import router as type_cache_admin_router
from app.api.routes.op_cache_admin import router as op_cache_admin_router
from app.api.routes.read_source_cache_admin import (
    router as read_source_cache_admin_router,
)
from app.api.routes.qty_cache_admin import router as qty_cache_admin_router
from app.api.routes.remark_cache_admin import router as remark_cache_admin_router
from app.api.routes.time_cache_admin import router as time_cache_admin_router
from app.api.routes.predict_cache_admin import router as predict_cache_admin_router
from app.api.routes.locate_cache_admin import router as locate_cache_admin_router
from app.api.routes.history_speak_cache_admin import (
    router as history_speak_cache_admin_router,
)
from app.api.routes.rule_gaps_admin import router as rule_gaps_admin_router
from app.api.routes.clinic import router as clinic_router
from app.api.routes.care_alert import router as care_alert_router
from app.api.routes.growth_trajectory import router as growth_trajectory_router

# 创建主路由，统一前缀 /v1
router = APIRouter(prefix="/v1")

# 注册子路由
router.include_router(health_router)
router.include_router(intent_router)
router.include_router(intent_cache_admin_router)
router.include_router(type_cache_admin_router)
router.include_router(op_cache_admin_router)
router.include_router(read_source_cache_admin_router)
router.include_router(qty_cache_admin_router)
router.include_router(remark_cache_admin_router)
router.include_router(time_cache_admin_router)
router.include_router(predict_cache_admin_router)
router.include_router(locate_cache_admin_router)
router.include_router(history_speak_cache_admin_router)
router.include_router(rule_gaps_admin_router)
router.include_router(clinic_router)
router.include_router(care_alert_router)
router.include_router(growth_trajectory_router)
