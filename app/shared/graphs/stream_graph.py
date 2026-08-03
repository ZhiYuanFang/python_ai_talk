"""
消费 LangGraph astream(custom+updates) → thinking 事件 + 终态

业务说明：
路由层只做 formatter：从统一图编排读取 custom thinking，合并 updates 得到最终 state。
进入消费时设置 GRAPH_STREAMING，便于嵌套 clinic 转发 custom。
"""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Dict, Tuple, Union

from app.shared.graphs.node_thinking import GRAPH_STREAMING

logger = logging.getLogger(__name__)

# ("thinking", payload) | ("final", state)
StreamItem = Tuple[str, Union[Dict[str, Any], Any]]


async def iter_graph_custom_thinking(
    graph: Any,
    initial_state: Dict[str, Any],
) -> AsyncIterator[StreamItem]:
    """
    执行图并逐步产出 thinking；最后产出 final state。

    Yields:
        ("thinking", {"type","node","content"}) 或 ("final", merged_state)
    """
    state: Dict[str, Any] = dict(initial_state)
    token = GRAPH_STREAMING.set(True)
    try:
        async for mode, chunk in graph.astream(
            initial_state,
            stream_mode=["custom", "updates"],
        ):
            if mode == "custom":
                if isinstance(chunk, dict) and chunk.get("content"):
                    yield "thinking", chunk
            elif mode == "updates":
                if isinstance(chunk, dict):
                    for patch in chunk.values():
                        if isinstance(patch, dict):
                            state.update(patch)
        yield "final", state
    finally:
        GRAPH_STREAMING.reset(token)


async def ainvoke_or_astream_forward(
    graph: Any,
    initial_state: Dict[str, Any],
    *,
    forward_custom: bool,
) -> Dict[str, Any]:
    """
    嵌套子图：流式时 astream 并向父 writer 转发 custom；否则 ainvoke。

    Args:
        graph: 编译后的子图（如 clinic_graph）
        initial_state: 子图输入
        forward_custom: 是否转发（通常等于 is_graph_streaming()）

    Returns:
        合并后的终态（含初始键）
    """
    if not forward_custom:
        result = await graph.ainvoke(initial_state)
        merged = dict(initial_state)
        if isinstance(result, dict):
            merged.update(result)
        return merged

    # 进入子图 astream 前固定父 writer，避免嵌套 context 抢写
    from langgraph.config import get_stream_writer

    parent_writer = None
    try:
        parent_writer = get_stream_writer()
    except Exception:
        parent_writer = None

    state: Dict[str, Any] = dict(initial_state)
    async for mode, chunk in graph.astream(
        initial_state,
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
                    state.update(patch)
    return state
