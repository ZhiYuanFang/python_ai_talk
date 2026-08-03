"""
喂养历史门禁：是否继续范围判断与拉取

业务说明：
clinic_graph 条件边与 clinic 流式动态 prepare_steps 共用同一判定，避免双份逻辑漂移。
force_needs_history 优先；needs_history 缺省按 true（兼容 tip / 旧 state）。
"""

from typing import Any, Dict


def should_fetch_history(state: Dict[str, Any]) -> bool:
    """
    是否应执行 judge_data_requirement + fetch_history。

    业务逻辑：
    1. force_needs_history 为真 → 必须拉
    2. needs_history 显式 False → 不拉
    3. 缺省 / None → 拉（fail-open）

    Args:
        state: 图或路由中的状态字典

    Returns:
        True 表示继续拉历史相关节点
    """
    if state.get("force_needs_history"):
        return True
    needs = state.get("needs_history")
    if needs is None:
        return True
    return bool(needs)
