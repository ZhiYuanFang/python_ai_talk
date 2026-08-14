"""
消费 LangGraph astream(custom+updates) → thinking 事件 + 终态

业务说明：
路由层只做 formatter：从统一图编排读取 custom thinking，合并 updates 得到最终 state。
进入消费时设置 GRAPH_STREAMING，便于嵌套 clinic 转发 custom。
终态合并走 apply_state_patch，保留补丁未提及的已有字段。
"""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Dict, Tuple, Union

from pydantic import BaseModel

from app.shared.graphs.node_thinking import GRAPH_STREAMING
from app.shared.graphs.state_patch import apply_state_patch

logger = logging.getLogger(__name__)

# ("thinking", payload) | ("final", state)
StreamItem = Tuple[str, Union[Dict[str, Any], Any]]


def _seed_state(initial_state: Any) -> Any:
    """流式合并起点：模型原样；dict 浅拷贝。"""
    if isinstance(initial_state, BaseModel):
        return initial_state
    if isinstance(initial_state, dict):
        return dict(initial_state)
    return initial_state


async def iter_graph_custom_thinking(
    graph: Any,
    initial_state: Any,
) -> AsyncIterator[StreamItem]:
    """
    执行图并逐步产出 thinking；最后产出 final state。

    Yields:
        ("thinking", {"type","node","content"}) 或 ("final", merged_state)
    """
    state = _seed_state(initial_state)
    token = GRAPH_STREAMING.set(True)
    try:
        # LangGraph 对 Pydantic 输入：若需 dict 则 model_dump（仅序列化边界）
        invoke_input = (
            initial_state.model_dump()
            if isinstance(initial_state, BaseModel)
            else initial_state
        )
        async for mode, chunk in graph.astream(
            invoke_input,
            stream_mode=["custom", "updates"],
        ):
            if mode == "custom":
                if isinstance(chunk, dict) and chunk.get("content"):
                    yield "thinking", chunk
            elif mode == "updates":
                if isinstance(chunk, dict):
                    for patch in chunk.values():
                        if isinstance(patch, dict):
                            state = apply_state_patch(state, patch)
        yield "final", state
    finally:
        GRAPH_STREAMING.reset(token)


async def ainvoke_or_astream_forward(
    graph: Any,
    initial_state: Any,
    *,
    forward_custom: bool,
) -> Any:
    """
    嵌套子图：流式时 astream 并向父 writer 转发 custom；否则 ainvoke。

    Returns:
        合并后的终态（含初始键）
    """
    invoke_input = (
        initial_state.model_dump()
        if isinstance(initial_state, BaseModel)
        else initial_state
    )
    if not forward_custom:
        result = await graph.ainvoke(invoke_input)
        merged = _seed_state(initial_state)
        if isinstance(result, BaseModel):
            return apply_state_patch(merged, result.model_dump(exclude_unset=True))
        if isinstance(result, dict):
            return apply_state_patch(merged, result)
        return merged

    from langgraph.config import get_stream_writer

    parent_writer = None
    try:
        parent_writer = get_stream_writer()
    except Exception:
        parent_writer = None

    state = _seed_state(initial_state)
    async for mode, chunk in graph.astream(
        invoke_input,
        stream_mode=["custom", "updates"],
    ):
        if mode == "custom" and isinstance(chunk, dict) and parent_writer is not None:
            if chunk.get("content"):
                try:
                    parent_writer(chunk)
                except Exception as e:
                    logger.debug(f"转发 custom 失败: {e}")
        elif mode == "updates" and isinstance(chunk, dict):
            for patch in chunk.values():
                if isinstance(patch, dict):
                    state = apply_state_patch(state, patch)
    return state
