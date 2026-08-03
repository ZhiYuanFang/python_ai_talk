"""Q&A 捷径、月龄带、通识硬过滤、feedback 下线。"""

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.shared.baby_age import age_band_from_months, calc_age_months, format_age_months_text
from app.shared.graphs.nodes.search_vectors import filter_knowledge_for_prompt
from app.shared.qa_fast_path import (
    evaluate_qa_hit,
    is_block_fast_path,
    promote_accepted_qa,
    rewrite_standalone_question,
)


def test_age_band_month_and_year():
    assert age_band_from_months(0) == "m0"
    assert age_band_from_months(11) == "m11"
    assert age_band_from_months(35) == "m35"
    assert age_band_from_months(36) == "y3"
    assert age_band_from_months(40) == "y3"
    assert age_band_from_months(None) is None


def test_calc_age_months_and_format():
    assert calc_age_months(date(2024, 1, 15), date(2024, 3, 14)) == 1
    assert calc_age_months(date(2024, 1, 15), date(2024, 3, 15)) == 2
    assert format_age_months_text(None) == "未知"
    assert format_age_months_text(8) == "8 个月"


def test_evaluate_qa_hit_thresholds():
    candidates = [
        {
            "id": "qa_1",
            "score": 0.81,
            "metadata": {
                "age_band": "m8",
                "quality_score": 0.75,
                "answer": "可以试试少量多次喂。",
                "standalone_question": "宝宝吐奶怎么办",
            },
        }
    ]
    hit, reason = evaluate_qa_hit(candidates, age_band="m8")
    assert reason == "hit"
    assert hit["answer"].startswith("可以试试")

    miss, reason = evaluate_qa_hit(candidates, age_band="m9")
    assert miss is None
    assert reason == "thresholds"

    low_sim = [
        {
            "id": "qa_2",
            "score": 0.79,
            "metadata": {
                "age_band": "m8",
                "quality_score": 0.9,
                "answer": "答",
            },
        }
    ]
    miss2, reason2 = evaluate_qa_hit(low_sim, age_band="m8")
    assert miss2 is None
    assert reason2 == "thresholds"

    unknown, reason3 = evaluate_qa_hit(candidates, age_band=None)
    assert unknown is None
    assert reason3 == "unknown_age"


def test_is_block_fast_path_force_and_sensitive():
    blocked, reason = is_block_fast_path({"force_needs_history": True})
    assert blocked and reason == "force_needs_history"
    blocked2, reason2 = is_block_fast_path({"question": "这个处方怎么吃"})
    assert blocked2 and reason2.startswith("sensitive")


def test_filter_knowledge_quality_hard_filter(monkeypatch):
    from app.config import settings as settings_mod

    monkeypatch.setattr(settings_mod.settings, "knowledge_quality_min", 0.7)
    monkeypatch.setattr(settings_mod.settings, "knowledge_min_score", 0.0)
    monkeypatch.setattr(settings_mod.settings, "knowledge_prompt_top_k", 5)

    results = [
        {
            "id": "low",
            "score": 0.95,
            "content": "低质",
            "metadata": {"quality_score": 0.5},
        },
        {
            "id": "ok",
            "score": 0.9,
            "content": "优质",
            "metadata": {"quality_score": 0.9},
        },
        {
            "id": "default",
            "score": 0.85,
            "content": "缺省质量",
            "metadata": {},
        },
    ]
    kept = filter_knowledge_for_prompt(results)
    ids = {x["id"] for x in kept}
    assert "low" not in ids
    assert "ok" in ids
    assert "default" in ids  # 缺省 0.8 >= 0.7


@pytest.mark.asyncio
async def test_rewrite_timeout_is_miss():
    async def _slow(*_a, **_k):
        import asyncio

        await asyncio.sleep(5)
        return type("R", (), {"content": "独立问句"})()

    with patch(
        "app.shared.qa_fast_path.llm_client.invoke",
        new=_slow,
    ):
        out = await rewrite_standalone_question(
            "那个怎么办",
            chat_context="近期陪伴对话",
            model_config={"provider": "deepseek", "name": "deepseek-chat"},
            timeout_s=0.05,
        )
    assert out is None


def test_promote_gates():
    class _FakeStore:
        def upsert_qa(self, **kwargs):
            return "qa_x"

    with patch("app.shared.vector_store.vector_store", _FakeStore()):
        assert promote_accepted_qa(
            standalone_question="", answer="a", age_band="m1"
        ) is None
        assert promote_accepted_qa(
            standalone_question="q", answer="a", age_band=""
        ) is None
        assert (
            promote_accepted_qa(
                standalone_question="吐奶怎么办",
                answer="少量多次",
                age_band="m8",
            )
            == "qa_x"
        )


def test_clinic_graph_qa_hit_skips_prepare():
    from app.clinic.graphs.clinic_graph import (
        _route_after_derive_age,
        _route_after_qa_search,
    )

    with patch("app.clinic.graphs.clinic_graph.settings") as mock_settings:
        mock_settings.qa_fast_path_enabled = True
        assert (
            _route_after_derive_age({"force_needs_history": True})
            == "judge_needs_history"
        )
        assert _route_after_derive_age({}) == "rewrite_standalone_question"

    assert _route_after_qa_search({"qa_hit": True}) == "format_qa_answer"
    assert _route_after_qa_search({"qa_hit": False}) == "judge_needs_history"


def test_feedback_routes_removed():
    from app.api.routes import clinic as clinic_routes
    from app.api.routes import tip as tip_routes

    app = FastAPI()
    app.include_router(clinic_routes.router, prefix="/v1")
    app.include_router(tip_routes.router, prefix="/v1")
    client = TestClient(app)

    r1 = client.post(
        "/v1/clinic/feedback",
        json={"answer_id": "x", "feedback": 1},
    )
    r2 = client.post(
        "/v1/tip/feedback",
        json={"answer_id": "y", "feedback": -1},
    )
    assert r1.status_code == 404
    assert r2.status_code == 404
