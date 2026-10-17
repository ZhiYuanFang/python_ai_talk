"""
流式 LLM 收集：透出 reasoning，聚合回答正文

业务说明：
对外 SSE 路径上的 LLM（分类、门禁、成长轨迹、澄清等）统一经本 helper
调用 llm_client.stream。开启思考时透出 reasoning；关闭时用固定字幕轮换。
正文增量聚合后返回。

设计思路：
1. thinking_enabled 时 reasoning 经 ThinkingSentenceCrRewriter（上句结束后下一句首 \\r）
   关闭时不转发 reasoning，改为 \\r努力思考中 / \\r正在思考中 每秒轮换
2. 默认经 emit_llm_thinking_delta 写入 LangGraph custom 流
3. 传入 on_thinking 时优先回调（图外 pending 等由路由注入 yield）
4. 聚合 answer content 返回；调用方自行解析 JSON，勿把半截 JSON 当 SSE answer
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

from app.shared.graphs.node_thinking import emit_llm_thinking_delta
from app.shared.graphs.thinking_sentence_cr import ThinkingSentenceCrRewriter
from app.shared.llm_client import LLMModelConfig, llm_client

logger = logging.getLogger(__name__)

# 思考增量回调：同步或异步均可
ThinkingCallback = Callable[[str], Union[None, Awaitable[None]]]

# 意图关闭模型思考后，用这两句按秒轮换，让客户端知道仍在处理
# 段首 \\r 清空上一句；\\r 后不加空格
_PULSE_PHRASES = ("\r努力思考中", "\r正在思考中")
_PULSE_INTERVAL_SEC = 1.0


async def _pulse_thinking(
    *,
    node_name: str,
    on_thinking: Optional[ThinkingCallback],
) -> None:
    """
    关闭模型思考时按秒轮换固定字幕。

    第一句由调用方在任务启动前立刻发出。本任务先等 1 秒再发下一句，
    之后在两句之间来回切换，直到被取消。
    """
    index = 1
    while True:
        await asyncio.sleep(_PULSE_INTERVAL_SEC)
        await _emit_thinking_piece(
            piece=_PULSE_PHRASES[index % 2],
            node_name=node_name,
            on_thinking=on_thinking,
        )
        index += 1


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
    2. thinking_enabled 时 reasoning 经句界 rewriter 透出；关闭时改为两句固定字幕按秒轮换，不转发 reasoning
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
    pulse_task: Optional[asyncio.Task] = None
    try:
        # 关闭思考：立刻打出第一句轮换，模型 reasoning 不转发
        if not thinking_enabled:
            await _emit_thinking_piece(
                piece=_PULSE_PHRASES[0],
                node_name=node_name,
                on_thinking=on_thinking,
            )
            pulse_task = asyncio.create_task(
                _pulse_thinking(node_name=node_name, on_thinking=on_thinking)
            )
        async for chunk in llm_client.stream(
            messages=messages,
            model_config=model_config,
            system_prompt=system_prompt,
            thinking_enabled=thinking_enabled,
        ):
            # 开启思考才透出 reasoning；句界后下一句首 \\r
            if thinking_enabled and chunk.thinking:
                for piece in cr.feed(chunk.thinking):
                    await _emit_thinking_piece(
                        piece=piece,
                        node_name=node_name,
                        on_thinking=on_thinking,
                    )
            if chunk.content:
                parts.append(chunk.content)
        # 流结束：不发裸 \\r，保留最后一句字幕
        if thinking_enabled:
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
    finally:
        # 调用结束或失败都停掉轮换，避免字幕在请求结束后继续跳
        if pulse_task is not None:
            pulse_task.cancel()
            try:
                await pulse_task
            except (asyncio.CancelledError, Exception):
                # 取消是正常收尾；轮换失败不拖垮正文聚合
                pass
    return "".join(parts).strip()
