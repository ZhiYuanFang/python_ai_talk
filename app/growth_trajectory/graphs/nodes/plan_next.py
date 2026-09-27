"""
plan_next 节点

业务说明：
在 confirm 之后或每轮问答后决定 enough|ask|reconfirm|final_ask。
禁止仅凭 confirm_prior 直接 generate；enough 或满轮在未做末问时均走 final_ask；
末问（final_free_text）完成后方可 generate。
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from app.growth_trajectory.graphs.nodes.prompts.ask import build_ask_user_message
from app.growth_trajectory.graphs.nodes.prompts.plan import build_plan_user_message
from app.growth_trajectory.graphs.nodes.prompts.system import (
    GROWTH_TRAJECTORY_SYSTEM_PROMPT,
)
from app.growth_trajectory.graphs.nodes.question_utils import (
    invoke_llm_json,
    normalize_question_payload,
)
from app.shared.graphs.state_patch import state_get

logger = logging.getLogger(__name__)

# 末轮自由补充：引导与 7 日阶梯相关的自述
_FINAL_PROMPT = (
    "这是最后一次提问，请用自己的话补充：宝宝当前最拿手/刚学会的是什么、"
    "最近想尝试但还不稳的是什么，以及你最想知道未来几天可能出现的变化"
    "（前面没提到的细节也可一并写上）。"
)


def _final_ask_payload() -> Dict[str, Any]:
    """构造强制 free_text 末问题。"""
    question = normalize_question_payload(
        {
            "id": "final_free_text",
            "prompt": _FINAL_PROMPT,
            "format": "free_text",
            "choices": [],
        },
        prefer_choice=False,
    )
    if "这是最后一次提问" not in str(question.get("prompt") or ""):
        question["prompt"] = _FINAL_PROMPT
    question["format"] = "free_text"
    question["choices"] = []
    return question


async def plan_next(state: Any) -> Dict[str, Any]:
    """
    规划下一步：enough/满轮 → final_ask（若未做）；已末问 → generate；否则 ask/reconfirm。

    Returns:
        plan_decision + 可选 pending_question
    """
    structured_round = int(state_get(state, "structured_round") or 0)
    max_rounds = int(state_get(state, "max_structured_rounds") or 6)
    final_ask_done = bool(state_get(state, "final_ask_done"))
    horizon = int(state_get(state, "horizon_days") or 7)

    # 已满 6 轮且未做过末问 → 强制 final_free_text（一次）
    if structured_round >= max_rounds and not final_ask_done:
        logger.info(
            "plan_next → final_ask (round=%s/%s)",
            structured_round,
            max_rounds,
        )
        return {
            "plan_decision": "final_ask",
            "pending_question": _final_ask_payload(),
            "phase": "plan",
        }

    # 满轮且已做过末问 → 直接生成
    if structured_round >= max_rounds and final_ask_done:
        return {
            "plan_decision": "generate",
            "pending_question": None,
            "phase": "plan",
        }

    data = await invoke_llm_json(
        state,
        system_prompt=GROWTH_TRAJECTORY_SYSTEM_PROMPT,
        user_message=build_plan_user_message(
            horizon_days=horizon,
            baby_age_months=state_get(state, "baby_age_months"),
            baby_profile=state_get(state, "baby_profile") or {},
            history_events=state_get(state, "history_events") or [],
            prior_feedback=state_get(state, "prior_feedback") or [],
            qa_so_far=state_get(state, "qa_so_far") or [],
            structured_round=structured_round,
            max_structured_rounds=max_rounds,
        ),
    )

    decision = "ask"
    reason = ""
    question_raw: Any = None
    if isinstance(data, dict):
        decision = str(data.get("decision") or "ask").strip().lower()
        reason = str(data.get("reason") or "").strip()
        question_raw = data.get("question")

    if decision not in ("enough", "ask", "reconfirm"):
        decision = "ask"

    # 首轮且几乎无问答时，避免过早 enough（至少问一轮更稳）
    qa_so_far = state_get(state, "qa_so_far") or []
    structured_qa = [
        q
        for q in qa_so_far
        if isinstance(q, dict) and q.get("kind") != "confirm_prior"
    ]
    if decision == "enough" and structured_round == 0 and not structured_qa:
        decision = "ask"
        reason = reason or "首轮仍建议补问关键信息"

    # enough：未做末问 → final_ask；已做末问 → generate
    if decision == "enough":
        if not final_ask_done:
            logger.info("plan_next → final_ask (enough): %s", reason)
            return {
                "plan_decision": "final_ask",
                "pending_question": _final_ask_payload(),
                "phase": "plan",
            }
        logger.info("plan_next → generate (enough, final done): %s", reason)
        return {
            "plan_decision": "generate",
            "pending_question": None,
            "phase": "plan",
        }

    # 缺 question 时再调 ask 提示词；再失败用模板
    if not isinstance(question_raw, dict):
        ask_data = await invoke_llm_json(
            state,
            system_prompt=GROWTH_TRAJECTORY_SYSTEM_PROMPT,
            user_message=build_ask_user_message(
                horizon_days=horizon,
                baby_age_months=state_get(state, "baby_age_months"),
                baby_profile=state_get(state, "baby_profile") or {},
                qa_so_far=qa_so_far,
                structured_round=structured_round,
                max_structured_rounds=max_rounds,
                plan_reason=reason,
            ),
        )
        question_raw = ask_data

    # 细挖默认不强行 choice；由模型 format 决定
    prefer_choice = True
    if isinstance(question_raw, dict):
        fmt = str(question_raw.get("format") or "").strip().lower()
        if fmt == "free_text":
            prefer_choice = False

    question = normalize_question_payload(
        question_raw,
        default_id=f"ask_{structured_round + 1}",
        default_prompt=(
            "请具体说说宝宝现在已经会什么、还不会什么"
            "（例如会不会扶站、有没有想迈步），以及最近最明显的变化。"
        ),
        prefer_choice=prefer_choice,
    )
    logger.info(
        "plan_next → %s id=%s round=%s",
        decision,
        question.get("id"),
        structured_round,
    )
    return {
        "plan_decision": decision,
        "pending_question": question,
        "phase": "plan",
    }
