"""
护理留意分析编排服务

业务说明：
将 HTTP 请求转为图初始状态，执行 care_alert_graph，返回 items。
不扣 clinic 配额；VIP 由 Go 传入首选 model，非 VIP 可省略走免费保底序。
不调用通识向量检索；kg_context 不硬塞进判定。
analyze 成功后写入 suggestionId → 建议快照（供 prompt 飞轮归因）。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.care_alert.graphs.care_alert_graph import care_alert_graph
from app.care_alert.schemas.care_alert import CareAlertAnalyzeRequest
from app.care_alert.services.flywheel_store import (
    care_alert_flywheel_store,
    snapshot_from_item,
)
from app.care_alert.services.model_resolve import resolve_model_config
from app.shared.history_window import enum_to_unix
from app.tip.graphs.nodes.derive_baby_age import shanghai_now

logger = logging.getLogger(__name__)


def _care_alert_window() -> tuple:
    """近两日 Unix 窗（昨 00:00 上海 → now）。"""
    return enum_to_unix("last_2_days")


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
        camelCase items 列表（有史+legend 时至少 1 条；否则可为空）

    Raises:
        ValueError: 模型解析失败（传了非法 model）
        Exception: 图/LLM 底层异常向上抛，由路由转 500
    """
    # None → 空 dict，节点侧解析为无首选
    model_config = resolve_model_config(request.model) or {}
    day = _resolve_day(request.day)

    initial_state: Dict[str, Any] = {
        "device_no": request.device_no,
        "day": day,
        "model_config": model_config,
        # 近两日、不限 event_ids，拉多条供间隔/缺记判断
        "data_requirement": {
            "event_ids": [],
            # 近两日（昨 00:00 上海 → now），缩短拉取与提示词
            "start_time": _care_alert_window()[0],
            "end_time": _care_alert_window()[1],
            "limit": 60,
        },
        "history_summary": request.history_summary,
        # kg_context 仅保留观测；不进 prompt / 飞轮
        "kg_context": request.kg_context,
    }

    # 请求透传月龄：resolve_baby_age 在画像无生日时回退
    if request.age_months is not None:
        initial_state["baby_age_months"] = int(request.age_months)

    logger.info(
        "护理留意分析开始: device_no=%s day=%s provider=%s name=%s age=%s",
        request.device_no,
        day,
        model_config.get("provider") or "(fallback-only)",
        model_config.get("name") or "-",
        request.age_months,
    )

    final_state: Dict[str, Any] = dict(initial_state)
    async for event in care_alert_graph.astream(initial_state, stream_mode="values"):
        if isinstance(event, dict):
            final_state = event

    # 本仓历史为空时可用编排侧历史列表补齐后重跑生成
    history_events = final_state.get("history_events") or []
    history_seeded = False
    if not history_events:
        seeded = _history_from_summary(request.history_summary)
        if seeded:
            logger.info("本仓历史为空，使用编排侧 history_summary: n=%s", len(seeded))
            final_state["history_events"] = seeded
            history_seeded = True

    if request.kg_context not in (None, {}, [], ""):
        logger.info(
            "护理留意收到 kg_context，按无知识库策略不注入 prompt device_no=%s",
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

    # 飞轮快照：每条 suggestion → 归因字段（非 knowledge_ids）
    for item in items:
        if not isinstance(item, dict):
            continue
        sid = str(item.get("suggestionId") or item.get("suggestion_id") or "").strip()
        if not sid:
            continue
        snap = snapshot_from_item(item, device_no=request.device_no, day=day)
        await care_alert_flywheel_store.save_snapshot(sid, snap)

    logger.info(
        "护理留意分析结束: device_no=%s day=%s count=%s",
        request.device_no,
        day,
        len(items),
    )
    return items
