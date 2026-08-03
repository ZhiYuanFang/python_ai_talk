"""grounded-bestie 提示词约束：有据点名 / 无据不编 / 约 50 字。"""

from app.clinic.graphs.nodes.prompts.clinic_answer import (
    build_clinic_answer_system_prompt,
    build_clinic_answer_user_message,
)
from app.tip.graphs.nodes.prompts.tip_answer import (
    build_tip_answer_system_prompt,
    build_tip_answer_user_message,
)


def test_clinic_system_has_grounded_bestie_rules():
    text = build_clinic_answer_system_prompt()
    assert "带过娃" in text or "有经验" in text or "听过很多吐槽" in text
    assert "有据必点名" in text
    assert "只作背景" not in text
    assert "约 50 字" in text
    assert "不要做疾病诊断" in text


def test_clinic_user_history_only_requires_cite():
    msg = build_clinic_answer_user_message(
        question="夜里又醒怎么办",
        history_events=[
            {
                "eventName": "喂奶",
                "startTime": "今天凌晨 2:10",
            }
        ],
        knowledge_results=[],
        baby_profile={"gender": "女"},
        chat_context=None,
        baby_age_months=6,
    )
    assert "必须结合喂养记录" in msg
    assert "点名 1 条" in msg
    assert "不要编造「上次」或「记录里」" not in msg


def test_clinic_user_chat_only_requires_prior_turn():
    msg = build_clinic_answer_user_message(
        question="还是好累",
        history_events=[],
        knowledge_results=[],
        baby_profile={},
        chat_context="近期陪伴对话（从旧到新）：\n第1轮-家长：夜里又醒\n第1轮-闺蜜：先眯会儿",
        baby_age_months=None,
    )
    assert "必须结合近期陪伴对话" in msg
    assert "点名上次" in msg


def test_clinic_user_neither_forbids_fabricated_memory():
    msg = build_clinic_answer_user_message(
        question="哈哈你好",
        history_events=[],
        knowledge_results=[],
        baby_profile={},
        chat_context="",
        baby_age_months=None,
    )
    assert "不要编造「上次」或「记录里」" in msg
    assert "必须结合喂养记录" not in msg
    assert "必须结合近期陪伴对话" not in msg


def test_tip_prompts_aligned():
    sys_text = build_tip_answer_system_prompt()
    assert "点名" in sys_text
    assert "约 50 字" in sys_text
    assert "禁止编造" in sys_text

    with_hist = build_tip_answer_user_message(
        event_info={"event_id": "1", "event_name": "喂奶"},
        baby_age_months=3,
        history_events=[{"eventName": "喂奶", "startTime": "1小时前"}],
        knowledge_results=[],
        baby_profile={},
        chat_context=None,
    )
    assert "必须结合近期喂养记录" in with_hist

    neither = build_tip_answer_user_message(
        event_info={"event_id": "1", "event_name": "喂奶"},
        baby_age_months=None,
        history_events=[],
        knowledge_results=[],
        baby_profile={},
        chat_context="",
    )
    assert "不要编造「上次」或「记录里」" in neither
