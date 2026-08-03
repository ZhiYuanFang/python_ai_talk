"""
LangGraph 节点思考：custom stream writer

业务说明：
在节点业务逻辑之前经 get_stream_writer 推送 thinking，供 astream(stream_mode=custom) 消费。
ainvoke 时 writer 仍可能存在但无路由消费者，调用保持安全。

设计思路：
1. with_node_thinking 包装任意 sync/async 节点
2. payload 约定：{type, node, content}
3. GRAPH_STREAMING ContextVar：嵌套 clinic astream 时向外转发 custom
"""

from __future__ import annotations

import asyncio
import contextvars
import inspect
import logging
from typing import Any, Awaitable, Callable, Dict, Union

from langgraph.config import get_stream_writer

logger = logging.getLogger(__name__)

NodeFn = Callable[
    [Dict[str, Any]],
    Union[Dict[str, Any], Awaitable[Dict[str, Any]]],
]

# 路由层 astream 消费时置 True，供 call_clinic_agent 选择内层 astream 并转发
GRAPH_STREAMING: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "graph_streaming", default=False
)


def is_graph_streaming() -> bool:
    """当前是否处于统一流式编排消费中。"""
    return bool(GRAPH_STREAMING.get())


def emit_thinking(node_name: str, content: str) -> None:
    """
    向当前图 custom 流写入一条 thinking；无 writer 时静默跳过。
    """
    try:
        writer = get_stream_writer()
    except Exception:
        return
    if writer is None:
        return
    try:
        writer(
            {
                "type": "thinking",
                "node": node_name,
                "content": content,
            }
        )
    except Exception as e:
        logger.debug(f"emit_thinking 忽略: node={node_name}, err={e}")


def with_node_thinking(
    node_name: str,
    node_fn: NodeFn,
    get_message: Callable[[str], str],
) -> NodeFn:
    """
    包装节点：先推 thinking 文案，再执行原节点。

    Args:
        node_name: 图节点名（与 thinking_messages 映射一致）
        node_fn: 原节点函数
        get_message: 节点名 → 中文 thinking
    """

    async def _async_wrapped(state: Dict[str, Any]) -> Dict[str, Any]:
        emit_thinking(node_name, get_message(node_name))
        # 让出事件循环，使 astream(custom) 消费者先收到 thinking 再进慢逻辑
        await asyncio.sleep(0)
        result = node_fn(state)
        if inspect.isawaitable(result):
            result = await result
        return result if isinstance(result, dict) else {}

    # 统一用 async 包装，LangGraph 支持 async 节点
    _async_wrapped.__name__ = getattr(node_fn, "__name__", node_name)
    _async_wrapped.__qualname__ = getattr(node_fn, "__qualname__", node_name)
    return _async_wrapped
