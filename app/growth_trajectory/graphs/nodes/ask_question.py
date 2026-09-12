"""
ask_question / reconfirm / final_free_text 节点

业务说明：
三者均 interrupt；ask 与 reconfirm 递增 structured_round；final 标记 final_ask_done。
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from langgraph.types import interrupt

from app.growth_trajectory.graphs.nodes.question_utils import (
    interrupt_value_to_answer,
    normalize_question_payload,
)
from app.shared.graphs.state_patch import state_get

logger = logging.getLogger(__name__)


def _pending_or_fallback(state: Any, *, kind: str) -> Dict[str, Any]:
    """取出 plan 写入的 pending_question，缺则给兜底题。"""
    raw = state_get(state, "pending_question")
    if kind == "final_ask":
        return normalize_question_payload(
            raw
            or {
                "id": "final_free_text",
                "prompt": (
                    "这是最后一次提问，请补充你认为最重要的近期情况。"
                ),
                "format": "free_text",
                "choices": [],
            },
            prefer_choice=False,
        )
    return normalize_question_payload(
        raw,
        default_id=f"{kind}_{int(state_get(state, 'structured_round') or 0) + 1}",
        default_prompt="请再补充一点宝宝近期的情况",
        prefer_choice=True,
    )


async def ask_question(state: Any) -> Dict[str, Any]:
    """结构化提问：interrupt 后计入 structured_round。"""
    question = _pending_or_fallback(state, kind="ask")
    resume_value = interrupt(question)
    answer = interrupt_value_to_answer(resume_value, question)
    answer["kind"] = "ask"

    qa = list(state_get(state, "qa_so_far") or [])
    qa.append(answer)
    round_n = int(state_get(state, "structured_round") or 0) + 1
    logger.info("ask_question 完成: round=%s id=%s", round_n, question.get("id"))
    return {
        "qa_so_far": qa,
        "structured_round": round_n,
        "pending_question": None,
        "phase": "after_ask",
    }


async def reconfirm(state: Any) -> Dict[str, Any]:
    """防选错再确认：interrupt 后计入 structured_round。"""
    question = _pending_or_fallback(state, kind="reconfirm")
    resume_value = interrupt(question)
    answer = interrupt_value_to_answer(resume_value, question)
    answer["kind"] = "reconfirm"

    qa = list(state_get(state, "qa_so_far") or [])
    qa.append(answer)
    round_n = int(state_get(state, "structured_round") or 0) + 1
    logger.info("reconfirm 完成: round=%s id=%s", round_n, question.get("id"))
    return {
        "qa_so_far": qa,
        "structured_round": round_n,
        "pending_question": None,
        "phase": "after_reconfirm",
    }


async def final_free_text(state: Any) -> Dict[str, Any]:
    """
    满 6 轮后的最后一次自由补充；不计 structured_round（已满），标记 final_ask_done。
    """
    question = _pending_or_fallback(state, kind="final_ask")
    # 强制文案含「这是最后一次提问」
    prompt = str(question.get("prompt") or "")
    if "这是最后一次提问" not in prompt:
        question["prompt"] = (
            "这是最后一次提问，请用一两句话补充你认为最重要、"
            "但前面没提到的近期情况。"
        )
    question["format"] = "free_text"
    question["choices"] = []

    resume_value = interrupt(question)
    answer = interrupt_value_to_answer(resume_value, question)
    answer["kind"] = "final_free_text"

    qa = list(state_get(state, "qa_so_far") or [])
    qa.append(answer)
    logger.info("final_free_text 完成: session=%s", state_get(state, "session_id"))
    return {
        "qa_so_far": qa,
        "final_ask_done": True,
        "pending_question": None,
        "phase": "after_final_ask",
        "plan_decision": "generate",
    }
