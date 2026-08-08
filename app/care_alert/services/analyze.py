"""
护理留意分析编排服务

业务说明：
将 HTTP 请求转为图初始状态，执行 care_alert_graph，返回 items。
不扣 clinic 配额；模型由 Go 指定（deepseek / zhipu）。
准确优先：不用未过门槛的 kg_context 硬塞进 knowledge。
analyze 成功后写入 suggestionId → knowledge_ids 飞轮映射。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.care_alert.graphs.care_alert_graph import care_alert_graph
from app.care_alert.schemas.care_alert import CareAlertAnalyzeRequest
from app.care_alert.services.flywheel_store import (
    care_alert_flywheel_store,
    suggestion_ids_from_items,
)
from app.care_alert.services.model_resolve import resolve_model_config
from app.shared.companion_session import extract_knowledge_ids
from app.tip.graphs.nodes.derive_baby_age import shanghai_now

logger = logging.getLogger(__name__)

# 向量检索查询：覆盖间隔/缺记/进行中过久等留意主题
_KG_QUERY = "宝宝护理留意 喂养间隔偏长 进行中过久 突然没有记录 同月龄注意"


def _resolve_day(day: Optional[str]) -> str:
    """逻辑日缺省为上海今天 YYYY-MM-DD。"""
    if day and str(day).strip():
        return str(day).strip()
    return shanghai_now().date().isoformat()


def _history_from_summary(history_summary: Any) -> Optional[List[Dict[str, Any]]]:
    """
    若 Go 透传了可用历史列表则取出，供跳过空拉取后的补充。

    业务逻辑：
    - list[dict] 直接用
    - dict 含 events/items 列表则取之
    - 其它返回 None（走本仓拉取）
    """
    if isinstance(history_summary, list):
        events = [e for e in history_summary if isinstance(e, dict)]
        return events or None
    if isinstance(history_summary, dict):
        for key in ("events", "items", "history", "historyEvents"):
            raw = history_summary.get(key)
            if isinstance(raw, list):
                events = [e for e in raw if isinstance(e, dict)]
                if events:
                    return events
    return None


async def run_care_alert_analyze(request: CareAlertAnalyzeRequest) -> List[Dict[str, Any]]:
    """
    执行护理留意日分析。

    Args:
        request: 已校验的分析请求

    Returns:
        camelCase items 列表（可为空）

    Raises:
        ValueError: 模型解析失败
        Exception: 图/LLM 底层异常向上抛，由路由转 500
    """
    model_config = resolve_model_config(request.model)
    day = _resolve_day(request.day)

    initial_state: Dict[str, Any] = {
        "device_no": request.device_no,
        "day": day,
        "model_config": model_config,
        # 供 search_vectors 使用
        "question": _KG_QUERY,
        # 近 7 天、不限 event_ids，拉多条供间隔/缺记判断
        "data_requirement": {
            "event_ids": [],
            "time_range": "last_7_days",
            "limit": 80,
        },
        "history_summary": request.history_summary,
        # kg_context 仅保留在 state 供观测；不再填入 knowledge（准确优先）
        "kg_context": request.kg_context,
    }

    # 请求透传月龄：resolve_baby_age 在画像无生日时回退
    if request.age_months is not None:
        initial_state["baby_age_months"] = int(request.age_months)

    logger.info(
        "护理留意分析开始: device_no=%s day=%s provider=%s name=%s age=%s",
        request.device_no,
        day,
        model_config.get("provider"),
        model_config.get("name"),
        request.age_months,
    )

    final_state: Dict[str, Any] = dict(initial_state)
    async for event in care_alert_graph.astream(initial_state, stream_mode="values"):
        if isinstance(event, dict):
            final_state = event

    # 本仓历史为空时可用编排侧历史列表补齐后重跑生成（史可补；通识不硬塞）
    history_events = final_state.get("history_events") or []
    history_seeded = False
    if not history_events:
        seeded = _history_from_summary(request.history_summary)
        if seeded:
            logger.info("本仓历史为空，使用编排侧 history_summary: n=%s", len(seeded))
            final_state["history_events"] = seeded
            history_seeded = True

    # 准确优先：向量门槛后 knowledge 为空则保持空，不用 kg_context 顶替
    knowledge = final_state.get("knowledge") or []
    if not knowledge and request.kg_context not in (None, {}, [], ""):
        logger.info(
            "本仓知识为空且存在 kg_context，按准确优先不硬塞进 knowledge device_no=%s",
            request.device_no,
        )

    items = final_state.get("items")
    if not isinstance(items, list):
        items = []

    # 仅历史后补且原先 items 空时重跑 LLM
    if not items and history_seeded:
        from app.care_alert.graphs.nodes.generate_care_alerts import generate_care_alerts

        logger.info("历史由编排侧补齐后重跑 LLM 生成")
        regenerated = await generate_care_alerts(final_state)
        items = regenerated.get("items") or []

    # 飞轮映射：本轮进 prompt 的通识 ids → 各 suggestionId
    knowledge_ids = extract_knowledge_ids(final_state.get("knowledge") or [])
    for sid in suggestion_ids_from_items(items):
        await care_alert_flywheel_store.save_mapping(
            sid,
            device_no=request.device_no,
            day=day,
            knowledge_ids=knowledge_ids,
        )

    logger.info(
        "护理留意分析结束: device_no=%s day=%s count=%s knowledge_ids=%s",
        request.device_no,
        day,
        len(items),
        len(knowledge_ids),
    )
    return items
