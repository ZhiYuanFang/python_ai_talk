"""
成长轨迹 turn SSE 编排

业务说明：
start/restart：以 session_id 为 thread_id 启动图；
answer：Command(resume=answer) 同 thread 恢复；
interrupt → question + done；generate 完 → result + done。
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, AsyncGenerator, Dict, Optional, Union

from langgraph.types import Command

from app.care_alert.services.model_resolve import resolve_model_config
from app.growth_trajectory.graphs.growth_trajectory_graph import growth_trajectory_graph
from app.growth_trajectory.graphs.states.growth_trajectory_state import (
    GrowthTrajectoryState,
)
from app.growth_trajectory.schemas.growth_trajectory import GrowthTrajectoryTurnRequest
from app.shared.graphs.node_thinking import GRAPH_STREAMING
from app.shared.history_window import last_n_days
from app.shared.schemas.data_requirement import DataRequirement

logger = logging.getLogger(__name__)

# model 缺省时的默认（与 care_alert 路由临时默认对齐，便于联调）
DEFAULT_LLM_MODEL: Dict[str, Any] = {
    "provider": "aliyun_dashscope",
    "name": "deepseek-v4-flash",
    "max_in_flight": 50,
}


def resolve_turn_model(model: Any) -> Dict[str, Any]:
    """解析请求 model；空则用默认。"""
    if model is None or model == {} or model == "":
        return dict(DEFAULT_LLM_MODEL)
    try:
        return resolve_model_config(model)
    except ValueError:
        logger.warning("成长轨迹 model 无效，回退默认: %r", model)
        return dict(DEFAULT_LLM_MODEL)


def _sse(payload: Dict[str, Any]) -> str:
    """clinic 风格：data: {json}\\n\\n。"""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _extract_interrupt_value(chunk: Any) -> Optional[Dict[str, Any]]:
    """
    从 updates 块提取 interrupt payload。

    LangGraph 1.x：{'__interrupt__': (Interrupt(value=...),)}
    """
    if not isinstance(chunk, dict):
        return None
    interrupts = chunk.get("__interrupt__")
    if not interrupts:
        return None
    first = interrupts[0] if isinstance(interrupts, (list, tuple)) else interrupts
    value = getattr(first, "value", None)
    if value is None and isinstance(first, dict):
        value = first.get("value")
    if isinstance(value, dict):
        return value
    return None


def _question_event(question: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    """组装契约 question 事件。"""
    fmt = str(question.get("format") or "free_text")
    choices = question.get("choices") or []
    if not isinstance(choices, list):
        choices = []
    choices = [str(c) for c in choices]
    if fmt == "choice" and len(choices) != 2:
        # 兜底保证恰好 2
        while len(choices) < 2:
            choices.append("其他")
        choices = choices[:2]
    if fmt != "choice":
        choices = []
    return {
        "type": "question",
        "id": str(question.get("id") or ""),
        "prompt": str(question.get("prompt") or ""),
        "format": fmt if fmt in ("choice", "free_text") else "free_text",
        "choices": choices,
        "sessionId": session_id,
        "session_id": session_id,
    }


def build_initial_state(
    request: GrowthTrajectoryTurnRequest,
    *,
    session_id: str,
    llm_model: Dict[str, Any],
) -> Dict[str, Any]:
    """构造 start/restart 初始 state dict。"""
    window = last_n_days(7)
    state = GrowthTrajectoryState(
        device_no=request.device_no,
        session_id=session_id,
        horizon_days=int(request.horizon_days or 7),
        prior_feedback=list(request.prior_feedback or []),
        llm_model=llm_model,
        needs_history=True,
        data_requirement=DataRequirement(
            event_ids=[],
            start_time=window[0],
            end_time=window[1],
            limit=40,
        ),
        max_structured_rounds=6,
        phase="init",
    )
    return state.model_dump()


async def iter_growth_trajectory_sse(
    request: GrowthTrajectoryTurnRequest,
) -> AsyncGenerator[str, None]:
    """
    产出成长轨迹 SSE 字符串。

    Yields:
        data: {...}\\n\\n 事件（thinking/question/result/error/done）
    """
    action = (request.action or "").strip().lower()
    session_id = (request.session_id or "").strip()

    try:
        llm_model = resolve_turn_model(request.model)
    except Exception as e:
        yield _sse({"type": "error", "code": "MODEL_INVALID", "message": str(e)})
        yield _sse({"type": "done"})
        return

    if action == "answer":
        if not session_id:
            yield _sse(
                {
                    "type": "error",
                    "code": "SESSION_REQUIRED",
                    "message": "answer 需要 session_id",
                }
            )
            yield _sse({"type": "done"})
            return
        answer_payload: Union[Dict[str, Any], str] = {}
        if request.answer is not None:
            answer_payload = {
                "question_id": request.answer.question_id or "",
                "value": request.answer.value or "",
            }
        invoke_input: Any = Command(resume=answer_payload)
        config = {"configurable": {"thread_id": session_id}}
    elif action in ("start", "restart"):
        if not session_id:
            session_id = f"gt_{uuid.uuid4().hex}"
        invoke_input = build_initial_state(
            request, session_id=session_id, llm_model=llm_model
        )
        config = {"configurable": {"thread_id": session_id}}
    else:
        yield _sse(
            {
                "type": "error",
                "code": "ACTION_INVALID",
                "message": f"未知 action: {action}",
            }
        )
        yield _sse({"type": "done"})
        return

    logger.info(
        "成长轨迹 turn: action=%s device=%s session=%s",
        action,
        request.device_no,
        session_id,
    )

    token = GRAPH_STREAMING.set(True)
    result_markdown = ""
    interrupted = False
    try:
        async for mode, chunk in growth_trajectory_graph.astream(
            invoke_input,
            config,
            stream_mode=["custom", "updates"],
        ):
            if mode == "custom" and isinstance(chunk, dict):
                content = chunk.get("content")
                if content:
                    yield _sse({"type": "thinking", "content": str(content)})
                continue

            if mode != "updates" or not isinstance(chunk, dict):
                continue

            # interrupt → 推 question 并结束本 HTTP 响应
            q = _extract_interrupt_value(chunk)
            if q is not None:
                interrupted = True
                yield _sse(_question_event(q, session_id))
                yield _sse({"type": "done"})
                return

            # 收集 generate 节点产物
            for _node_name, patch in chunk.items():
                if _node_name == "__interrupt__":
                    continue
                if isinstance(patch, dict):
                    md = patch.get("result_markdown")
                    if isinstance(md, str) and md.strip():
                        result_markdown = md.strip()

        # 流正常结束：再查一次 state，防漏 interrupt / 漏 markdown
        if not interrupted:
            snap = await growth_trajectory_graph.aget_state(config)
            interrupts = getattr(snap, "interrupts", None) or ()
            if interrupts:
                first = interrupts[0]
                value = getattr(first, "value", None)
                if isinstance(value, dict):
                    yield _sse(_question_event(value, session_id))
                    yield _sse({"type": "done"})
                    return
            values = getattr(snap, "values", None) or {}
            if isinstance(values, dict):
                md = values.get("result_markdown") or result_markdown
                if isinstance(md, str) and md.strip():
                    result_markdown = md.strip()

        if result_markdown:
            yield _sse(
                {
                    "type": "result",
                    "markdown": result_markdown,
                    "sessionId": session_id,
                    "session_id": session_id,
                }
            )
        else:
            # 无结果也无 interrupt：视为异常空跑
            yield _sse(
                {
                    "type": "error",
                    "code": "EMPTY_RESULT",
                    "message": "未产生问题或结果，请 restart 重试",
                }
            )
        yield _sse({"type": "done"})
    except Exception as e:
        logger.error("成长轨迹 turn 失败: %s", e, exc_info=True)
        yield _sse(
            {
                "type": "error",
                "code": "GROWTH_TRAJECTORY_ERROR",
                "message": f"成长轨迹预测失败: {e}",
            }
        )
        yield _sse({"type": "done"})
    finally:
        GRAPH_STREAMING.reset(token)
