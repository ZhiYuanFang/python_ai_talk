"""
流式 LLM 收集：透出 reasoning，聚合回答正文

业务说明：
对外 SSE 路径上的 LLM（分类、门禁、成长轨迹、澄清等）统一经本 helper
调用 llm_client.stream(thinking_enabled=True)，将 reasoning 增量透出后聚合 content。

设计思路：
1. reasoning 经 ThinkingSentenceCrRewriter（上句结束后下一句首 \\r）
2. 默认经 emit_llm_thinking_delta 写入 LangGraph custom 流
3. 传入 on_thinking 时优先回调（图外 pending 等由路由注入 yield）
4. 聚合 answer content 返回；调用方自行解析 JSON，勿把半截 JSON 当 SSE answer
"""

from __future__ import annotations

import inspect
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

from app.shared.graphs.node_thinking import emit_llm_thinking_delta
from app.shared.graphs.thinking_sentence_cr import ThinkingSentenceCrRewriter
from app.shared.llm_client import LLMModelConfig, llm_client

logger = logging.getLogger(__name__)

# 思考增量回调：同步或异步均可
ThinkingCallback = Callable[[str], Union[None, Awaitable[None]]]


async def _emit_thinking_piece(
    *,
    piece: str,
    node_name: str,
    on_thinking: Optional[ThinkingCallback],
) -> None:
    """透出单条已改写的 thinking 片段。"""
    if not piece:
        return
    if on_thinking is not None:
        maybe = on_thinking(piece)
        if inspect.isawaitable(maybe):
            await maybe
    else:
        emit_llm_thinking_delta(node_name, piece)


async def stream_llm_collect(
    *,
    messages: List[Dict[str, str]],
    model_config: Optional[LLMModelConfig],
    system_prompt: Optional[str] = None,
    node_name: str = "llm",
    on_thinking: Optional[ThinkingCallback] = None,
    thinking_enabled: bool = True,
) -> str:
    """
    流式调用 LLM：透出 reasoning，返回聚合后的回答正文。

    业务逻辑：
    1. 调用 llm_client.stream（默认开启原生 thinking）
    2. thinking 增量经句界 rewriter 后：有 on_thinking 则回调，否则 emit_llm_thinking_delta
    3. 聚合 content 片段并 strip 后返回；失败返回空串

    Args:
        messages: 对话消息列表
        model_config: 模型配置（缺省时 stream 会抛错并由本函数吞掉返回空）
        system_prompt: 系统提示词
        node_name: 图节点名（emit 时写入 payload.node）
        on_thinking: 可选思考回调（图外 SSE 路由注入）
        thinking_enabled: 是否启用提供商原生思考（SSE 路径应为 True）

    Returns:
        聚合后的回答正文；失败或无内容时为空串
    """
    parts: List[str] = []
    cr = ThinkingSentenceCrRewriter()
    try:
        async for chunk in llm_client.stream(
            messages=messages,
            model_config=model_config,
            system_prompt=system_prompt,
            thinking_enabled=thinking_enabled,
        ):
            # reasoning：句界后下一句首 \\r；不在句末贴 \\r
            if chunk.thinking:
                for piece in cr.feed(chunk.thinking):
                    await _emit_thinking_piece(
                        piece=piece,
                        node_name=node_name,
                        on_thinking=on_thinking,
                    )
            if chunk.content:
                parts.append(chunk.content)
        # 流结束：不发裸 \\r，保留最后一句字幕
        for piece in cr.flush():
            await _emit_thinking_piece(
                piece=piece,
                node_name=node_name,
                on_thinking=on_thinking,
            )
    except Exception as e:
        logger.warning(
            "stream_llm_collect 失败: node=%s err=%s",
            node_name,
            e,
            exc_info=True,
        )
        return ""
    return "".join(parts).strip()
