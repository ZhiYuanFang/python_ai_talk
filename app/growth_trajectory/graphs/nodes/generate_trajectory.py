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
    """LLM 失败时的可读兜底 Markdown（整段注意点，禁止按日拆分）。"""
    age = "月龄未知" if age_months is None else f"约 {age_months} 个月"
    return (
        f"## 🌟 未来{horizon_days}天可能发生什么\n"
        f"- 结合当前信息（宝宝{age}），宝宝可能在大运动或作息上有小幅变化，"
        f"多观察精神与互动即可。\n\n"
        f"## ⚠️ 这几天需要注意什么\n"
        f"- 🛡️ 保证安全环境，满足探索需求但不勉强超能力动作。\n"
        f"- 💤 尽量保持规律作息，按需安抚。\n"
        f"- 👀 留意食欲与情绪波动，异常持续请就医。\n\n"
        f"## 🍼 结合近期喂养\n"
        f"- 喂养记录不足时已弱化推断；有记录时再细化辅食/奶量建议。\n\n"
        f"## 💛 小结\n"
        f"- 本结果仅供日常参考，期待宝宝稳步成长。\n"
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
