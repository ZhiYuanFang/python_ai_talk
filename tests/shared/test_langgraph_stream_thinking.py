"""LangGraph custom thinking + unified stream helpers."""

import asyncio
from typing import Any, Dict, TypedDict
import pytest
from langgraph.graph import END, StateGraph

from app.shared.graphs.node_thinking import (
    GRAPH_STREAMING,
    emit_thinking,
    is_graph_streaming,
    with_node_thinking,
)
from app.shared.graphs.stream_graph import (
    ainvoke_or_astream_forward,
    iter_graph_custom_thinking,
)


class _S(TypedDict, total=False):
    n: int
    flag: bool


def _msg(name: str) -> str:
    return f"think:{name}"


@pytest.mark.asyncio
async def test_custom_thinking_arrives_before_slow_work():
    """Spike 固化：thinking 在节点慢逻辑完成前被消费者收到。"""
    work_done = asyncio.Event()
    saw_custom_while_running = False

    async def slow(state: _S) -> Dict[str, Any]:
        await asyncio.sleep(0.2)
        work_done.set()
        return {"n": 1}

    g = StateGraph(_S)
    g.add_node("slow", with_node_thinking("slow", slow, _msg))
    g.set_entry_point("slow")
    g.add_edge("slow", END)
    graph = g.compile()

    async for mode, chunk in graph.astream(
        {"n": 0}, stream_mode=["custom", "updates"]
    ):
        if mode == "custom":
            assert chunk.get("content") == "think:slow\n"
            saw_custom_while_running = not work_done.is_set()
        elif mode == "updates":
            assert work_done.is_set()

    assert saw_custom_while_running is True


@pytest.mark.asyncio
async def test_ainvoke_safe_with_thinking_wrapper():
    async def node(state: _S) -> Dict[str, Any]:
        return {"n": 2}

    g = StateGraph(_S)
    g.add_node("n", with_node_thinking("n", node, _msg))
    g.set_entry_point("n")
    g.add_edge("n", END)
    graph = g.compile()
    out = await graph.ainvoke({"n": 0})
    assert out["n"] == 2


@pytest.mark.asyncio
async def test_iter_graph_custom_thinking_and_streaming_flag():
    async def node(state: _S) -> Dict[str, Any]:
        assert is_graph_streaming() is True
        return {"flag": True}

    g = StateGraph(_S)
    g.add_node("n", with_node_thinking("n", node, _msg))
    g.set_entry_point("n")
    g.add_edge("n", END)
    graph = g.compile()

    thinkings = []
    final = None
    assert is_graph_streaming() is False
    async for kind, payload in iter_graph_custom_thinking(graph, {"n": 0}):
        if kind == "thinking":
            thinkings.append(payload)
        else:
            final = payload
    assert is_graph_streaming() is False
    assert thinkings and thinkings[0]["content"] == "think:n\n"
    assert final and final.get("flag") is True


@pytest.mark.asyncio
async def test_nested_forward_uses_ainvoke_when_not_streaming():
    async def node(state: _S) -> Dict[str, Any]:
        return {"n": 9}

    g = StateGraph(_S)
    g.add_node("n", with_node_thinking("n", node, _msg))
    g.set_entry_point("n")
    g.add_edge("n", END)
    graph = g.compile()

    out = await ainvoke_or_astream_forward(graph, {"n": 0}, forward_custom=False)
    assert out["n"] == 9
    assert is_graph_streaming() is False


@pytest.mark.asyncio
async def test_clinic_gate_skip_no_fetch_thinking_in_stream():
    """门禁 false 时 custom 流不应出现 fetch_history 文案。"""
    from app.clinic.graphs.clinic_graph import clinic_graph
    from app.clinic.graphs.nodes.thinking_messages import get_thinking_message

    async def fake_gate(state):
        return {"needs_history": False, "history_events": []}

    async def boom_fetch(state):
        raise AssertionError("fetch_history should be skipped")

    # 用轻量图复现路由，不打真 LLM
    from app.shared.graphs.history_gate import should_fetch_history
    from app.shared.graphs.node_thinking import with_node_thinking
    from app.clinic.graphs.states.clinic_state import ClinicState

    async def noop(state):
        return {}

    def route(state):
        if should_fetch_history(state):
            return "fetch_history"
        return "fetch_baby_profile"

    msg = get_thinking_message
    wf = StateGraph(ClinicState)
    wf.add_node(
        "judge_needs_history",
        with_node_thinking("judge_needs_history", fake_gate, msg),
    )
    wf.add_node(
        "fetch_history",
        with_node_thinking("fetch_history", boom_fetch, msg),
    )
    wf.add_node(
        "fetch_baby_profile",
        with_node_thinking("fetch_baby_profile", noop, msg),
    )
    wf.set_entry_point("judge_needs_history")
    wf.add_conditional_edges(
        "judge_needs_history",
        route,
        {
            "fetch_history": "fetch_history",
            "fetch_baby_profile": "fetch_baby_profile",
        },
    )
    wf.add_edge("fetch_baby_profile", END)
    g = wf.compile()

    nodes = []
    async for kind, payload in iter_graph_custom_thinking(g, {"question": "hi"}):
        if kind == "thinking":
            nodes.append(payload.get("node"))
    assert "fetch_history" not in nodes
    assert "fetch_baby_profile" in nodes
    # clinic_graph 仍可 import（冒烟）
    assert clinic_graph is not None


def test_emit_thinking_no_crash_outside_graph():
    # 图外调用应静默
    emit_thinking("x", "y")
    token = GRAPH_STREAMING.set(True)
    try:
        assert is_graph_streaming()
    finally:
        GRAPH_STREAMING.reset(token)


def test_ensure_orchestration_thinking_content_idempotent():
    from app.shared.graphs.node_thinking import ensure_orchestration_thinking_content

    assert ensure_orchestration_thinking_content("字幕") == "字幕\n"
    assert ensure_orchestration_thinking_content("字幕\n") == "字幕\n"
