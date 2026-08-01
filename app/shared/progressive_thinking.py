"""
流式「先思考字幕、再执行节点」辅助

业务说明：
clinic / tip / intent 流式路径不再依赖 astream(updates) 的「完成后才报」。
对线性步骤：先让调用方 yield thinking，再执行节点并合并 state。

设计思路：
1. run_linear_steps_with_thinking：线性步骤表，逐步 yield (node_name, message)
2. 节点可为 sync 或 async：返回 awaitable 则 await，否则直接当 patch（兼容 match_event_by_vector）
3. 每步执行前 asyncio.sleep(0)，便于事件循环刷出 SSE
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from typing import Any, Awaitable, Callable, Dict, List, Tuple, Union

logger = logging.getLogger(__name__)

# 节点函数：sync 或 async，返回 patch dict
NodeFn = Callable[
    [Dict[str, Any]],
    Union[Dict[str, Any], Awaitable[Dict[str, Any]]],
]


async def _invoke_node(
    node_fn: NodeFn,
    state: Dict[str, Any],
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
    state: Dict[str, Any],
    steps: List[Tuple[str, NodeFn]],
    get_message: Callable[[str], str],
):
    """
    线性步进：对每步先 yield (node_name, thinking_text)，再执行节点并更新 state。

    业务逻辑：
    1. 调用方用 async for 收到 (name, text) 后立刻写 SSE
    2. 本函数在 yield 之后才执行节点（生成器协议：consumer 处理完 yield 值后才 resume）
    3. 因此「先输出思考再执行」成立；sync/async 节点均可

    Args:
        state: 可变状态字典（就地 update）
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
        if isinstance(patch, dict):
            state.update(patch)


async def run_one_step_with_thinking(
    state: Dict[str, Any],
    node_name: str,
    node_fn: NodeFn,
    get_message: Callable[[str], str],
):
    """
    单步：yield (name, text) 后执行。供 intent 条件分支使用。

    Yields:
        (node_name, thinking_text) 恰好一次，然后执行节点
    """
    yield node_name, get_message(node_name)
    await asyncio.sleep(0)
    patch = await _invoke_node(node_fn, state)
    if isinstance(patch, dict):
        state.update(patch)
