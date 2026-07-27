"""pending 澄清硬匹配与 LLM 映射回归。"""

from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.feeding.services.clarification import (
    PendingClarification,
    ResolveStatus,
    clarification_store,
    map_llm_clarify_payload,
    normalize_reply_text,
    resolve_free_text,
    try_hard_resolve,
)
from app.feeding.services.intent_pipeline import try_handle_pending


def _leaf_pending(**kwargs: Any) -> PendingClarification:
    defaults = dict(
        kind="leaf_confirm",
        conversation_id="cid-leaf",
        options=[
            {
                "event_id": "e-formula",
                "event_name": "奶粉",
                "extra_names": [],
            }
        ],
        clarify_message="您是要记录「奶粉」吗？",
        original_utterance="喂奶",
        action="one",
        quantity=None,
        match_source="vector",
        matched_vector_id="vec-old",
        model_config={"provider": "deepseek", "name": "deepseek-v4-flash"},
    )
    defaults.update(kwargs)
    return PendingClarification(**defaults)


def _parent_pending(**kwargs: Any) -> PendingClarification:
    defaults = dict(
        kind="parent_disambiguation",
        conversation_id="cid-parent",
        options=[
            {"event_id": "e-breast", "event_name": "母乳", "extra_names": []},
            {"event_id": "e-formula", "event_name": "奶粉", "extra_names": []},
        ],
        clarify_message="请选择具体事件",
        original_utterance="喂奶",
        action="one",
        quantity=None,
        match_source="vector",
        matched_vector_id="vec-old",
        parent_id="e-feed",
        parent_name="喂养",
        model_config={"provider": "deepseek", "name": "deepseek-v4-flash"},
    )
    defaults.update(kwargs)
    return PendingClarification(**defaults)


FULL_EVENTS: List[Dict[str, Any]] = [
    {"event_id": "e-feed", "event_name": "喂养", "parent_id": ""},
    {"event_id": "e-breast", "event_name": "母乳", "parent_id": "e-feed"},
    {"event_id": "e-formula", "event_name": "奶粉", "parent_id": "e-feed"},
    {"event_id": "e-diaper", "event_name": "换尿布", "parent_id": ""},
]


class TestNormalizeAndHardMatch:
    def test_normalize_strips_trailing_punct(self):
        assert normalize_reply_text("是的。") == "是的"
        assert normalize_reply_text("OK！") == "ok"

    def test_leaf_confirm_yes_with_period_hard_match(self):
        pending = _leaf_pending()
        result = try_hard_resolve("是的。", pending)
        assert result is not None
        assert result.status == ResolveStatus.RESOLVED
        assert result.event["event_id"] == "e-formula"
        assert result.action == "confirm"

    def test_compound_affirmative_misses_hard_match(self):
        pending = _leaf_pending()
        assert try_hard_resolve("是的，喂了30毫升", pending) is None

    def test_parent_bare_yes_misses_hard_match(self):
        # 父消歧下肯定词不走硬匹配，应交 LLM（通常 ask_again）
        pending = _parent_pending()
        assert try_hard_resolve("是的", pending) is None


class TestMapLlmPayload:
    def test_confirm_with_quantity(self):
        pending = _leaf_pending(quantity=10)
        result = map_llm_clarify_payload(
            {"action": "confirm", "quantity": 30},
            pending,
            FULL_EVENTS,
        )
        assert result.status == ResolveStatus.RESOLVED
        assert result.quantity == 30
        assert result.event["event_id"] == "e-formula"

    def test_correct_to_leaf(self):
        pending = _leaf_pending()
        result = map_llm_clarify_payload(
            {"action": "correct", "event_name": "母乳"},
            pending,
            FULL_EVENTS,
        )
        assert result.status == ResolveStatus.RESOLVED
        assert result.skip_vector_success is True
        assert result.event["event_id"] == "e-breast"

    def test_correct_to_parent(self):
        pending = _leaf_pending()
        result = map_llm_clarify_payload(
            {"action": "correct", "event_id": "e-feed"},
            pending,
            FULL_EVENTS,
        )
        assert result.status == ResolveStatus.RESOLVED
        assert result.event["event_id"] == "e-feed"
        assert result.skip_vector_success is True

    def test_confirm_forbidden_on_parent_disambiguation(self):
        pending = _parent_pending()
        result = map_llm_clarify_payload(
            {"action": "confirm"},
            pending,
            FULL_EVENTS,
        )
        assert result.status == ResolveStatus.ASK_AGAIN

    def test_new_intent(self):
        pending = _leaf_pending()
        result = map_llm_clarify_payload(
            {"action": "new_intent"},
            pending,
            FULL_EVENTS,
        )
        assert result.status == ResolveStatus.OFF_TOPIC

    def test_invalid_action_asks_again(self):
        pending = _leaf_pending()
        result = map_llm_clarify_payload({"action": "noop"}, pending, FULL_EVENTS)
        assert result.status == ResolveStatus.ASK_AGAIN

    def test_unknown_correct_target_asks_again(self):
        pending = _leaf_pending()
        result = map_llm_clarify_payload(
            {"action": "correct", "event_name": "不存在的事件"},
            pending,
            FULL_EVENTS,
        )
        assert result.status == ResolveStatus.ASK_AGAIN


@pytest.mark.asyncio
async def test_resolve_hard_match_does_not_call_llm():
    pending = _leaf_pending()
    with patch(
        "app.feeding.services.clarification.llm_resolve_pending_reply",
        new_callable=AsyncMock,
    ) as mock_llm:
        result = await resolve_free_text("是的。", pending, full_events=FULL_EVENTS)
        assert result.status == ResolveStatus.RESOLVED
        mock_llm.assert_not_called()


@pytest.mark.asyncio
async def test_llm_failure_asks_again():
    pending = _leaf_pending()
    with patch(
        "app.feeding.services.clarification.llm_client.invoke",
        new_callable=AsyncMock,
        side_effect=TimeoutError("timeout"),
    ):
        result = await resolve_free_text(
            "是的，喂了30毫升", pending, full_events=FULL_EVENTS
        )
        assert result.status == ResolveStatus.ASK_AGAIN


@pytest.mark.asyncio
async def test_llm_bad_json_asks_again():
    pending = _leaf_pending()
    mock_resp = MagicMock()
    mock_resp.content = "not-json"
    with patch(
        "app.feeding.services.clarification.llm_client.invoke",
        new_callable=AsyncMock,
        return_value=mock_resp,
    ):
        result = await resolve_free_text(
            "是的，喂了30毫升", pending, full_events=FULL_EVENTS
        )
        assert result.status == ResolveStatus.ASK_AGAIN


@pytest.mark.asyncio
async def test_pipeline_confirm_quantity_overwrite():
    clarification_store.clear("cid-q")
    pending = _leaf_pending(conversation_id="cid-q", quantity=5)
    clarification_store.set(pending)

    mock_resp = MagicMock()
    mock_resp.content = '{"action":"confirm","quantity":30}'
    with patch(
        "app.feeding.services.clarification.llm_client.invoke",
        new_callable=AsyncMock,
        return_value=mock_resp,
    ), patch(
        "app.feeding.services.intent_pipeline.event_vector_store"
    ) as mock_vs:
        mock_vs.add_user_expression = MagicMock()
        mock_vs.increment_success_count = MagicMock()
        mock_vs.check_and_cleanup = MagicMock()
        resp, as_new = await try_handle_pending(
            "是的，喂了30毫升", "cid-q", FULL_EVENTS
        )
        assert as_new is False
        assert resp is not None
        assert resp.event_id == "e-formula"
        assert resp.quantity == 30
        assert clarification_store.get("cid-q") is None


@pytest.mark.asyncio
async def test_pipeline_correct_leaf_direct_land_and_flywheel():
    clarification_store.clear("cid-c")
    pending = _leaf_pending(conversation_id="cid-c", match_source="vector")
    clarification_store.set(pending)

    mock_resp = MagicMock()
    mock_resp.content = '{"action":"correct","event_name":"母乳"}'
    with patch(
        "app.feeding.services.clarification.llm_client.invoke",
        new_callable=AsyncMock,
        return_value=mock_resp,
    ), patch(
        "app.feeding.services.intent_pipeline.event_vector_store"
    ) as mock_vs:
        mock_vs.add_user_expression = MagicMock()
        mock_vs.increment_success_count = MagicMock()
        mock_vs.check_and_cleanup = MagicMock()
        resp, as_new = await try_handle_pending(
            "不是的，是母乳", "cid-c", FULL_EVENTS
        )
        assert as_new is False
        assert resp is not None
        assert resp.need_confirm is False
        assert resp.event_id == "e-breast"
        mock_vs.add_user_expression.assert_called_once()
        call_kw = mock_vs.add_user_expression.call_args.kwargs
        assert call_kw["event_id"] == "e-breast"
        assert call_kw["expression"] == "喂奶"
        mock_vs.increment_success_count.assert_not_called()


@pytest.mark.asyncio
async def test_pipeline_correct_to_parent_disambiguates():
    clarification_store.clear("cid-p")
    pending = _leaf_pending(conversation_id="cid-p")
    clarification_store.set(pending)

    mock_resp = MagicMock()
    mock_resp.content = '{"action":"correct","event_id":"e-feed"}'
    with patch(
        "app.feeding.services.clarification.llm_client.invoke",
        new_callable=AsyncMock,
        return_value=mock_resp,
    ):
        resp, as_new = await try_handle_pending(
            "不是，是喂养", "cid-p", FULL_EVENTS
        )
        assert as_new is False
        assert resp is not None
        assert resp.need_confirm is True
        assert resp.confirm_type == "parent_disambiguation"
        new_pending = clarification_store.get("cid-p")
        assert new_pending is not None
        assert new_pending.kind == "parent_disambiguation"
        assert new_pending.matched_vector_id == ""


@pytest.mark.asyncio
async def test_pipeline_llm_fail_keeps_pending():
    clarification_store.clear("cid-f")
    pending = _leaf_pending(conversation_id="cid-f")
    clarification_store.set(pending)

    with patch(
        "app.feeding.services.clarification.llm_client.invoke",
        new_callable=AsyncMock,
        side_effect=RuntimeError("boom"),
    ):
        resp, as_new = await try_handle_pending(
            "是的，喂了30毫升", "cid-f", FULL_EVENTS
        )
        assert as_new is False
        assert resp is not None
        assert resp.need_confirm is True
        assert clarification_store.get("cid-f") is not None


@pytest.mark.asyncio
async def test_pipeline_new_intent_clears_pending():
    clarification_store.clear("cid-n")
    pending = _leaf_pending(conversation_id="cid-n")
    clarification_store.set(pending)

    mock_resp = MagicMock()
    mock_resp.content = '{"action":"new_intent"}'
    with patch(
        "app.feeding.services.clarification.llm_client.invoke",
        new_callable=AsyncMock,
        return_value=mock_resp,
    ):
        resp, as_new = await try_handle_pending(
            "今天天气怎么样", "cid-n", FULL_EVENTS
        )
        assert resp is None
        assert as_new is True
        assert clarification_store.get("cid-n") is None
