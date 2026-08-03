"""needs-history gate: should_fetch_history + parse + force + fetch guard."""

from unittest.mock import AsyncMock, patch

import pytest

from app.shared.graphs.history_gate import should_fetch_history
from app.shared.graphs.nodes.fetch_history import fetch_history
from app.shared.graphs.nodes.judge_needs_history import (
    _parse_needs_history,
    judge_needs_history,
)


def test_should_fetch_history_force_wins():
    assert should_fetch_history({"force_needs_history": True, "needs_history": False})
    assert should_fetch_history({"force_needs_history": True})


def test_should_fetch_history_explicit_false():
    assert not should_fetch_history({"needs_history": False})


def test_should_fetch_history_missing_defaults_true():
    assert should_fetch_history({})
    assert should_fetch_history({"needs_history": None})
    assert should_fetch_history({"needs_history": True})


def test_parse_needs_history_bool_and_fail_open():
    assert _parse_needs_history('{"needs_history": false}') is False
    assert _parse_needs_history('{"needs_history": true}') is True
    assert _parse_needs_history("```json\n{\"needs_history\": false}\n```") is False
    assert _parse_needs_history("not-json") is True
    assert _parse_needs_history("{}") is True


@pytest.mark.asyncio
async def test_judge_force_skips_llm():
    with patch(
        "app.shared.graphs.nodes.judge_needs_history.llm_client.invoke",
        new_callable=AsyncMock,
    ) as mock_invoke:
        result = await judge_needs_history(
            {
                "force_needs_history": True,
                "question": "今天好累啊",
                "model_config": {"provider": "openai", "name": "gpt"},
            }
        )
        assert result == {"needs_history": True}
        mock_invoke.assert_not_called()


@pytest.mark.asyncio
async def test_judge_false_clears_history_events():
    mock_resp = AsyncMock()
    mock_resp.content = '{"needs_history": false}'
    with patch(
        "app.shared.graphs.nodes.judge_needs_history.llm_client.invoke",
        new_callable=AsyncMock,
        return_value=mock_resp,
    ):
        result = await judge_needs_history(
            {
                "question": "今天天气怎么样",
                "model_config": {"provider": "openai", "name": "gpt"},
            }
        )
        assert result == {"needs_history": False, "history_events": []}


@pytest.mark.asyncio
async def test_fetch_history_guard_skips_http():
    with patch(
        "app.shared.graphs.nodes.fetch_history.http_client.get_filtered_history_events",
        new_callable=AsyncMock,
    ) as mock_filter:
        with patch(
            "app.shared.graphs.nodes.fetch_history.http_client.get_history_events",
            new_callable=AsyncMock,
        ) as mock_all:
            out = await fetch_history(
                {
                    "device_no": "d1",
                    "needs_history": False,
                    "data_requirement": {
                        "event_ids": [],
                        "time_range": "last_7_days",
                        "limit": 20,
                    },
                }
            )
            assert out == {"history_events": []}
            mock_filter.assert_not_called()
            mock_all.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_history_force_still_fetches():
    with patch(
        "app.shared.graphs.nodes.fetch_history.http_client.get_filtered_history_events",
        new_callable=AsyncMock,
        return_value=[{"eventName": "吃奶"}],
    ) as mock_filter:
        out = await fetch_history(
            {
                "device_no": "d1",
                "needs_history": False,
                "force_needs_history": True,
                "data_requirement": {
                    "event_ids": ["1"],
                    "time_range": "last_7_days",
                    "limit": 20,
                },
            }
        )
        assert out["history_events"] == [{"eventName": "吃奶"}]
        mock_filter.assert_awaited_once()


def test_clinic_graph_routes_and_skip_knowledge_combo():
    from app.clinic.graphs.clinic_graph import (
        _route_after_fetch_history,
        _route_after_needs_history,
    )

    assert _route_after_needs_history({"needs_history": True}) == "judge_data_requirement"
    assert _route_after_needs_history({"needs_history": False}) == "search_vectors"
    assert (
        _route_after_needs_history(
            {"needs_history": False, "skip_knowledge": True}
        )
        == "fetch_baby_profile"
    )
    # force 覆盖 false
    assert (
        _route_after_needs_history(
            {"needs_history": False, "force_needs_history": True}
        )
        == "judge_data_requirement"
    )
    assert _route_after_fetch_history({"skip_knowledge": True}) == "fetch_baby_profile"
    assert _route_after_fetch_history({}) == "search_vectors"
