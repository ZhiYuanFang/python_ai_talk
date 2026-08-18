"""
流式「先思考字幕、再执行节点」辅助（遗留）

业务说明：
主路径已改为 LangGraph astream(custom) + with_node_thinking（见
app.shared.graphs.node_thinking / stream_graph）。
本模块保留供回滚或偶发脚本，路由层不应再依赖。

设计思路（历史）：
1. run_linear_steps_with_thinking：线性步骤表，逐步 yield (node_name, message)
2. 节点可为 sync 或 async：返回 awaitable 则 await，否则直接当 patch
3. 每步执行前 asyncio.sleep(0)，便于事件循环刷出 SSE
4. 补丁合并走 apply_state_patch，兼容 Pydantic State（禁止假定 dict.update）
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from typing import Any, Awaitable, Callable, Dict, List, Tuple, Union

from app.shared.graphs.state_patch import apply_state_patch

logger = logging.getLogger(__name__)

# 节点函数：sync 或 async，返回 patch dict；state 可为 Pydantic 或 dict
NodeFn = Callable[
    [Any],
    Union[Dict[str, Any], Awaitable[Dict[str, Any]]],
]


def _merge_patch_into_state(state: Any, patch: Any) -> Any:
    """
    将节点补丁合并进 State。

    业务逻辑：
    - 统一走 apply_state_patch（Pydantic / dict 均可）
    - 若原 state 为 dict，就地 clear+update，保留旧调用方「可变 dict」语义
    - 若为 Pydantic，返回新模型；生成器内后续步骤使用该返回值
    """
    if not isinstance(patch, dict):
        return state
    merged = apply_state_patch(state, patch)
    if isinstance(state, dict) and isinstance(merged, dict):
        state.clear()
        state.update(merged)
        return state
    return merged


async def _invoke_node(
    node_fn: NodeFn,
    state: Any,
) -> Any:
    """
    调用图节点：兼容 sync（直接返回 dict）与 async（coroutine）。

    业务逻辑：
    先调用 node_fn；若结果 isawaitable 再 await，避免对 dict 错误 await。
    """
    result = node_fn(state)
    if inspect.isawaitable(result):
        return await result
    return result


async def run_linear_steps_with_thinking(
    state: Any,
    steps: List[Tuple[str, NodeFn]],
    get_message: Callable[[str], str],
):
    """
    线性步进：对每步先 yield (node_name, thinking_text)，再执行节点并更新 state。

    业务逻辑：
    1. 调用方用 async for 收到 (name, text) 后立刻写 SSE
    2. 本函数在 yield 之后才执行节点（生成器协议：consumer 处理完 yield 值后才 resume）
    3. 因此「先输出思考再执行」成立；sync/async 节点均可
    4. 补丁经 apply_state_patch 合并，兼容 Pydantic State

    Args:
        state: 图 State（Pydantic 或 dict）
        steps: [(节点名, 节点函数), ...]
        get_message: 节点名 → 中文 thinking 文案

    Yields:
        (node_name, thinking_text)
    """
    for node_name, node_fn in steps:
        text = get_message(node_name)
        # 先把字幕交给调用方 yield 到客户端
        yield node_name, text
        # 让出事件循环，利于 StreamingResponse 刷出上一包
        await asyncio.sleep(0)
        try:
            patch = await _invoke_node(node_fn, state)
        except Exception as e:
            logger.error(f"步进节点执行失败 node={node_name}: {e}", exc_info=True)
            raise
        state = _merge_patch_into_state(state, patch)


async def run_one_step_with_thinking(
    state: Any,
    node_name: str,
    node_fn: NodeFn,
    get_message: Callable[[str], str],
):
    """
    单步：yield (name, text) 后执行。供 intent 条件分支使用。

    Args:
        state: 图 State（Pydantic 或 dict）

    Yields:
        (node_name, thinking_text) 恰好一次，然后执行节点
    """
    yield node_name, get_message(node_name)
    await asyncio.sleep(0)
    patch = await _invoke_node(node_fn, state)
    _merge_patch_into_state(state, patch)
