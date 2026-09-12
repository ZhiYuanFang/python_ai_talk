"""
generate 节点：产出未来 horizon_days 天 Markdown
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from app.growth_trajectory.graphs.nodes.prompts.generate import (
    build_generate_user_message,
)
from app.growth_trajectory.graphs.nodes.prompts.system import (
    GROWTH_TRAJECTORY_SYSTEM_PROMPT,
)
from app.growth_trajectory.graphs.nodes.question_utils import invoke_llm_text
from app.shared.graphs.state_patch import state_get

logger = logging.getLogger(__name__)


def _fallback_markdown(*, horizon_days: int, age_months: Any) -> str:
    """LLM 失败时的可读兜底 Markdown。"""
    age = "月龄未知" if age_months is None else f"约 {age_months} 个月"
    days = "\n".join(
        f"### 第{i}天\n- 观察精神与食欲；保持规律作息；按需安抚。\n"
        for i in range(1, max(1, horizon_days) + 1)
    )
    return (
        f"# 未来{horizon_days}天成长轨迹\n\n"
        f"## 总览\n"
        f"结合当前信息（宝宝{age}）给出温和观察建议；"
        f"非医疗诊断，如有不适请就医。\n\n"
        f"## 按日建议\n{days}\n"
        f"## 温馨提示\n"
        f"- 本结果仅供日常参考。\n"
        f"- 喂养记录不足时已弱化喂养相关推断。\n"
    )


async def generate_trajectory(state: Any) -> Dict[str, Any]:
    """调用 LLM 生成 Markdown；失败用模板兜底。"""
    horizon = int(state_get(state, "horizon_days") or 7)
    age = state_get(state, "baby_age_months")
    text = await invoke_llm_text(
        state,
        system_prompt=GROWTH_TRAJECTORY_SYSTEM_PROMPT,
        user_message=build_generate_user_message(
            horizon_days=horizon,
            baby_age_months=age,
            baby_profile=state_get(state, "baby_profile") or {},
            history_events=state_get(state, "history_events") or [],
            prior_feedback=state_get(state, "prior_feedback") or [],
            qa_so_far=state_get(state, "qa_so_far") or [],
        ),
    )
    if not text or len(text.strip()) < 20:
        text = _fallback_markdown(horizon_days=horizon, age_months=age)
        logger.warning("generate 使用兜底 Markdown")
    else:
        logger.info("generate 完成: chars=%s", len(text))
    return {
        "result_markdown": text.strip(),
        "phase": "done",
        "plan_decision": "done",
        "pending_question": None,
    }
