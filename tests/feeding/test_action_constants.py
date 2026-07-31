"""共享协议常量与喂养 action 存储约定回归。"""

from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import MagicMock

from app.feeding.services.clarification import (
    PendingClarification,
    pending_to_response_fields,
)
from app.feeding.services.event_vector_store import (
    EventVectorStore,
    _ACTION_DOCUMENT_PREFIX,
)
from app.shared.constants import (
    ConfirmType,
    IntentAction,
    MatchSource,
    STANDARD_INTENT_ACTIONS,
    TargetType,
    VectorSource,
)
from app.config.settings import Settings


def test_standard_intent_actions_are_english():
    assert [a.value for a in STANDARD_INTENT_ACTIONS] == ["start", "end", "one"]
    for action in STANDARD_INTENT_ACTIONS:
        assert action.value in _ACTION_DOCUMENT_PREFIX
        assert _ACTION_DOCUMENT_PREFIX[action.value]  # 中文表面语料存在


def test_add_standard_event_writes_english_metadata_and_chinese_documents():
    store = EventVectorStore.__new__(EventVectorStore)
    store._initialized = True
    captured: Dict[str, Any] = {}

    def fake_upsert(**kwargs):
        captured.update(kwargs)

    store._collection = MagicMock()
    store._collection.upsert.side_effect = fake_upsert
    store._embed = MagicMock(return_value=[[0.1], [0.2], [0.3], [0.4]])

    store._add_standard_event(event_id="3", event_name="睡眠")

    ids: List[str] = captured["ids"]
    documents: List[str] = captured["documents"]
    metadatas: List[Dict[str, Any]] = captured["metadatas"]

    assert "std_3_base" in ids
    assert "std_3_start" in ids
    assert "std_3_end" in ids
    assert "std_3_one" in ids
    assert not any("开始" in i or "结束" in i or "记录" in i for i in ids)

    by_id = {i: (d, m) for i, d, m in zip(ids, documents, metadatas)}
    assert by_id["std_3_start"][0] == "开始睡眠"
    assert by_id["std_3_start"][1]["action"] == IntentAction.START.value
    assert by_id["std_3_start"][1]["source"] == VectorSource.STANDARD.value
    assert by_id["std_3_end"][0] == "结束睡眠"
    assert by_id["std_3_end"][1]["action"] == IntentAction.END.value
    assert by_id["std_3_one"][0] == "记录睡眠"
    assert by_id["std_3_one"][1]["action"] == IntentAction.ONE.value
    assert by_id["std_3_base"][1]["action"] == ""


def test_pending_response_keeps_feeding_action_not_disambiguate():
    pending = PendingClarification(
        kind=ConfirmType.PARENT_DISAMBIGUATION.value,
        conversation_id="cid-1",
        options=[
            {"event_id": "e1", "event_name": "午睡"},
            {"event_id": "e2", "event_name": "夜睡"},
        ],
        clarify_message="请选择",
        original_utterance="开始睡觉",
        action=IntentAction.START.value,
        match_source=MatchSource.VECTOR.value,
        parent_name="睡眠",
    )
    fields = pending_to_response_fields(pending)
    assert fields["need_confirm"] is True
    assert fields["confirm_type"] == ConfirmType.PARENT_DISAMBIGUATION.value
    assert fields["action"] == IntentAction.START.value
    assert fields["action"] != "disambiguate"
    assert fields["target_type"] == TargetType.FEEDING.value
    assert fields["options"][0]["action"] == IntentAction.START.value


def test_rebuild_feeding_standard_events_defaults_false():
    assert Settings.model_fields["rebuild_feeding_standard_events"].default is False


def test_initialize_events_with_empty_dict_deletes_standard_only():
    """initialize_events([]) 仍会清 standard；启动路径必须在调用前确认字典非空。"""
    store = EventVectorStore.__new__(EventVectorStore)
    store._initialized = True
    store._collection = MagicMock()
    store._collection.get.return_value = {"ids": ["std_1_start"]}
    store._embed = MagicMock(return_value=[])

    store.initialize_events([])
    store._collection.delete.assert_called_once_with(ids=["std_1_start"])
    store._collection.upsert.assert_not_called()
