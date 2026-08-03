"""
隐式飞轮节点（clinic 图入口）

业务说明：
对会话 last_suggestion 做接受/拒绝/说不清三态判定并驱动质量飞轮。
失败不中断主流程。置于数据准备之前，便于流式 custom thinking 覆盖该段耗时。
"""

import logging
from typing import Any, Dict

from app.shared.suggestion_acceptance import maybe_apply_implicit_feedback

logger = logging.getLogger(__name__)


async def implicit_feedback(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    隐式采纳判定节点。

    Returns:
        空 patch（副作用写会话/向量分）
    """
    device_no = str(state.get("device_no") or "")
    question = str(state.get("question") or state.get("user_input") or "")
    model_config = dict(state.get("model_config") or {})
    try:
        await maybe_apply_implicit_feedback(device_no, question, model_config)
    except Exception as e:
        logger.error(f"隐式飞轮异常（不中断主流程）: {e}", exc_info=True)
    return {}
