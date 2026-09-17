"""
护理留意分析编排服务

业务说明：
将 HTTP 请求转为图初始状态，执行 care_alert_graph，返回 items。
不扣 clinic 配额；model 由 Go 传入（含 VIP 选型），Python 不换模。
不调用通识向量检索；无 feedback 飞轮快照。
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.care_alert.graphs.care_alert_graph import care_alert_graph
from app.care_alert.graphs.states.care_alert_state import CareAlertState
from app.care_alert.schemas.care_alert import CareAlertAnalyzeRequest
from app.care_alert.services.model_resolve import resolve_model_config
from app.shared.graphs.node_thinking import GRAPH_STREAMING
from app.shared.graphs.state_patch import state_get
from app.shared.history_window import last_n_days
from app.shared.schemas.data_requirement import DataRequirement
from app.shared.baby_age import shanghai_now

logger = logging.getLogger(__name__)


def _care_alert_window() -> tuple:
    """最近N天 Unix 窗。"""
    return last_n_days(2)


def _resolve_day(day: Optional[str]) -> str:
    """逻辑日缺省为上海今天 YYYY-MM-DD。"""
    # if day and str(day).strip():
    #     return str(day).strip()
    return shanghai_now().strftime("%Y-%m-%d %H:%M")


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
    # Go 必传 model；解析失败由 resolve 抛错
    llm_model = resolve_model_config(request.model)
    day = _resolve_day(request.day)
    window = _care_alert_window()

    care_alert_state = CareAlertState(
        device_no=request.device_no,
        day=day,
        llm_model=llm_model,
        data_requirement=DataRequirement(
            event_ids=[],
            start_time=window[0],
            end_time=window[1],
            limit=60,
        ),
        history_summary=request.history_summary,
        kg_context=request.kg_context,
        baby_age_months=(
            int(request.age_months) if request.age_months is not None else None
        ),
    )

    logger.info(
        "护理留意分析开始: device_no=%s day=%s provider=%s name=%s age=%s",
        request.device_no,
        day,
        llm_model.get("provider") or "(missing)",
        llm_model.get("name") or "-",
        request.age_months,
    )

    # LangGraph 边界：Pydantic State 序列化为 dict 传入 astream
    graph_input = care_alert_state.model_dump()
    final_state: Any = graph_input
    async for event in care_alert_graph.astream(graph_input, stream_mode="values"):
        if isinstance(event, dict):
            final_state = event

    # 本仓历史为空时可用编排侧历史列表补齐后重跑生成
    history_events = state_get(final_state, "history_events") or []
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

    items = state_get(final_state, "items")
    if not isinstance(items, list):
        items = []

    # 仅历史后补且原先 items 空时重跑 LLM
    if not items and history_seeded:
        from app.care_alert.graphs.nodes.generate_care_alerts import generate_care_alerts

        logger.info("历史由编排侧补齐后重跑 LLM 生成")
        regenerated = await generate_care_alerts(final_state)
        items = regenerated.get("items") or []

    logger.info(
        "护理留意分析结束: device_no=%s day=%s count=%s",
        request.device_no,
        day,
        len(items),
    )
    return items


def _sse(payload: Dict[str, Any]) -> str:
    """clinic 风格：data: {json}\\n\\n。"""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _build_care_alert_graph_input(request: CareAlertAnalyzeRequest) -> tuple[Dict[str, Any], str, Dict[str, Any]]:
    """构造图初始 state、day、llm_model。"""
    llm_model = resolve_model_config(request.model)
    day = _resolve_day(request.day)
    window = _care_alert_window()
    care_alert_state = CareAlertState(
        device_no=request.device_no,
        day=day,
        llm_model=llm_model,
        data_requirement=DataRequirement(
            event_ids=[],
            start_time=window[0],
            end_time=window[1],
            limit=60,
        ),
        history_summary=request.history_summary,
        kg_context=request.kg_context,
        baby_age_months=(
            int(request.age_months) if request.age_months is not None else None
        ),
    )
    return care_alert_state.model_dump(), day, llm_model


async def _finalize_care_alert_items(
    request: CareAlertAnalyzeRequest,
    final_state: Any,
    day: str,
) -> List[Dict[str, Any]]:
    """与阻塞路径一致：补历史、必要时重跑生成。"""
    history_events = state_get(final_state, "history_events") or []
    history_seeded = False
    if not history_events:
        seeded = _history_from_summary(request.history_summary)
        if seeded:
            logger.info("本仓历史为空，使用编排侧 history_summary: n=%s", len(seeded))
            final_state["history_events"] = seeded
            history_seeded = True

    items = state_get(final_state, "items")
    if not isinstance(items, list):
        items = []

    if not items and history_seeded:
        from app.care_alert.graphs.nodes.generate_care_alerts import generate_care_alerts

        logger.info("历史由编排侧补齐后重跑 LLM 生成")
        regenerated = await generate_care_alerts(final_state)
        items = regenerated.get("items") or []

    return items


async def iter_care_alert_analyze_sse(
    request: CareAlertAnalyzeRequest,
) -> AsyncGenerator[str, None]:
    """
    护理留意分析 SSE：thinking 增量 + 终态 result(items) + done。

    Yields:
        data: {...}\\n\\n
    """
    try:
        graph_input, day, llm_model = _build_care_alert_graph_input(request)
    except ValueError as e:
        yield _sse({"type": "error", "code": "MODEL_INVALID", "message": str(e)})
        yield _sse({"type": "done"})
        return

    logger.info(
        "护理留意 SSE 分析开始: device_no=%s day=%s provider=%s name=%s",
        request.device_no,
        day,
        llm_model.get("provider") or "(missing)",
        llm_model.get("name") or "-",
    )

    token = GRAPH_STREAMING.set(True)
    final_state: Any = graph_input
    try:
        async for mode, chunk in care_alert_graph.astream(
            graph_input,
            stream_mode=["custom", "values"],
        ):
            if mode == "custom" and isinstance(chunk, dict):
                content = chunk.get("content")
                if content:
                    yield _sse({"type": "thinking", "content": str(content)})
                continue
            if mode == "values" and isinstance(chunk, dict):
                final_state = chunk

        items = await _finalize_care_alert_items(request, final_state, day)
        yield _sse(
            {
                "type": "result",
                "day": day,
                "items": items,
            }
        )
        yield _sse({"type": "done"})
        logger.info(
            "护理留意 SSE 分析结束: device_no=%s day=%s count=%s",
            request.device_no,
            day,
            len(items),
        )
    except Exception as e:
        logger.error("护理留意 SSE 分析失败: %s", e, exc_info=True)
        yield _sse(
            {
                "type": "error",
                "code": "CARE_ALERT_ERROR",
                "message": f"护理留意分析失败: {e}",
            }
        )
        yield _sse({"type": "done"})
    finally:
        GRAPH_STREAMING.reset(token)
