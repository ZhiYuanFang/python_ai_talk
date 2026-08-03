"""原生流式 thinking：reasoning_content 映射与编排换行规则。"""

from types import SimpleNamespace
from typing import Any, AsyncIterator, List
from unittest.mock import MagicMock

import pytest

from app.shared.graphs.node_thinking import ensure_orchestration_thinking_content
from app.shared.llm_client import (
    LLMClient,
    LLMModelConfig,
    extract_stream_thinking_and_content,
)


class _FakeRedisGate:
    def acquire(self, *_args: Any, **_kwargs: Any) -> "_FakeRedisGate":
        return self

    async def __aenter__(self) -> "_FakeRedisGate":
        return self

    async def __aexit__(self, *_args: Any) -> bool:
        return False


def test_extract_reasoning_from_delta_and_additional_kwargs():
    thinking, content = extract_stream_thinking_and_content(
        SimpleNamespace(reasoning_content="先看夜里", content=None)
    )
    assert thinking == "先看夜里"
    assert content == ""

    thinking, content = extract_stream_thinking_and_content(
        SimpleNamespace(
            content="你好",
            additional_kwargs={"reasoning_content": "想一句"},
        )
    )
    assert thinking == "想一句"
    assert content == "你好"

    thinking, content = extract_stream_thinking_and_content(
        {"reasoning_content": "A", "content": "B"}
    )
    assert thinking == "A"
    assert content == "B"


def test_orchestration_thinking_newline_helper():
    assert ensure_orchestration_thinking_content("正在翻翻记录…") == "正在翻翻记录…\n"
    assert ensure_orchestration_thinking_content("已有\n") == "已有\n"
    assert ensure_orchestration_thinking_content("") == ""


@pytest.mark.asyncio
async def test_stream_thinking_maps_reasoning_without_trailing_newline(monkeypatch):
    """thinking_enabled 时带 extra_body，映射 reasoning，且 thinking 不加尾部 \\n。"""
    client = LLMClient()
    monkeypatch.setattr(client, "_get_redis_gate", lambda: _FakeRedisGate())

    captured: dict[str, Any] = {}

    class _Delta:
        def __init__(self, reasoning: str | None = None, content: str | None = None):
            self.reasoning_content = reasoning
            self.content = content

    class _Chunk:
        def __init__(self, reasoning: str | None = None, content: str | None = None):
            self.choices = [SimpleNamespace(delta=_Delta(reasoning, content))]

    async def fake_create(**kwargs: Any) -> AsyncIterator[Any]:
        captured["kwargs"] = kwargs

        async def _gen() -> AsyncIterator[Any]:
            yield _Chunk(reasoning="先看夜里喂养", content=None)
            yield _Chunk(reasoning=None, content="今天先观察")
            yield _Chunk(reasoning="再补一句", content="就好")

        return _gen()

    mock_lc = MagicMock()
    mock_lc.root_async_client.chat.completions.create = fake_create
    # 确认缓存客户端未被写入永久 extra_body
    mock_lc.extra_body = None
    monkeypatch.setattr(client, "_get_client", lambda *_a, **_k: mock_lc)

    outs: List[Any] = []
    async for item in client.stream(
        [{"role": "user", "content": "夜里闹怎么办"}],
        LLMModelConfig(provider="deepseek", name="deepseek-chat"),
        thinking_enabled=True,
    ):
        outs.append(item)

    assert captured["kwargs"]["extra_body"] == {"thinking": {"type": "enabled"}}
    assert mock_lc.extra_body is None
    assert outs[0].thinking == "先看夜里喂养"
    assert not outs[0].thinking.endswith("\n")
    assert outs[0].content == ""
    assert outs[1].thinking == ""
    assert outs[1].content == "今天先观察"
    assert outs[2].thinking == "再补一句"
    assert outs[2].content == "就好"


@pytest.mark.asyncio
async def test_stream_without_thinking_does_not_send_extra_body(monkeypatch):
    client = LLMClient()
    monkeypatch.setattr(client, "_get_redis_gate", lambda: _FakeRedisGate())

    create_called = {"n": 0}

    async def boom_create(**_kwargs: Any) -> None:
        create_called["n"] += 1
        raise AssertionError("thinking 关闭时不应走 raw OpenAI create")

    async def fake_astream(_messages: Any) -> AsyncIterator[Any]:
        yield SimpleNamespace(content="仅正文")

    mock_lc = MagicMock()
    mock_lc.root_async_client.chat.completions.create = boom_create
    mock_lc.astream = fake_astream
    monkeypatch.setattr(client, "_get_client", lambda *_a, **_k: mock_lc)

    outs = [
        item
        async for item in client.stream(
            [{"role": "user", "content": "hi"}],
            LLMModelConfig(provider="glm", name="glm-4"),
            thinking_enabled=False,
        )
    ]
    assert create_called["n"] == 0
    assert len(outs) == 1
    assert outs[0].content == "仅正文"
    assert outs[0].thinking == ""
