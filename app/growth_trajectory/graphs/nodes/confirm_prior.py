"""
confirm_prior 节点

业务说明：
有 prior_feedback 时 interrupt 确认；不计入 structured_round；确认后必须走 plan_next。
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from langgraph.types import interrupt

from app.growth_trajectory.graphs.nodes.prompts.confirm import build_confirm_user_message
from app.growth_trajectory.graphs.nodes.prompts.system import (
    GROWTH_TRAJECTORY_SYSTEM_PROMPT,
)
from app.growth_trajectory.graphs.nodes.question_utils import (
    interrupt_value_to_answer,
    invoke_llm_json,
    normalize_question_payload,
)
from app.shared.graphs.state_patch import state_get

logger = logging.getLogger(__name__)


async def confirm_prior(state: Any) -> Dict[str, Any]:
    """
    历史反馈确认（不计 6 轮）。

    业务逻辑：
    1. 用 LLM（失败则模板）生成二选一确认题
    2. interrupt 挂起；resume 后写入 qa_so_far（标记 kind=confirm_prior）
    3. 置 confirmed_prior=True，不递增 structured_round
    """
    prior = state_get(state, "prior_feedback") or []
    data = await invoke_llm_json(
        state,
        system_prompt=GROWTH_TRAJECTORY_SYSTEM_PROMPT,
        user_message=build_confirm_user_message(prior_feedback=prior),
    )
    question = normalize_question_payload(
        data,
        default_id="confirm_prior",
        default_prompt="上次的轨迹反馈还适用于现在吗？",
        prefer_choice=True,
    )

    # interrupt：首次暂停并把 question 暴露给路由；resume 后得到作答
    resume_value = interrupt(question)
    answer = interrupt_value_to_answer(resume_value, question)
    answer["kind"] = "confirm_prior"

    qa = list(state_get(state, "qa_so_far") or [])
    qa.append(answer)
    logger.info(
        "confirm_prior 完成: session=%s value=%s",
        state_get(state, "session_id"),
        answer.get("value"),
    )
    return {
        "confirmed_prior": True,
        "qa_so_far": qa,
        "pending_question": None,
        "phase": "after_confirm",
    }
