"""
上一条建议的隐式采纳判定

业务说明：
前端已去掉显式采纳按钮。clinic 续聊时根据用户本轮话术，
对会话中 last_suggestion 做 accepted / rejected / unclear 三态判定，
驱动知识飞轮质量分；判定失败可下次重试（不置 feedback_applied）。

设计思路：
1. 先做轻量关键词启发，命中则直接返回
2. 否则调用 LLM 输出 JSON status
3. 异常返回 None，由调用方不标记 applied
"""

from __future__ import annotations

import json
import logging
import re
from enum import Enum
from typing import Any, Dict, Optional

from app.shared.llm_client import LLMModelConfig, llm_client

logger = logging.getLogger(__name__)


class AcceptanceStatus(str, Enum):
    """三态：接受 / 拒绝 / 说不清。"""

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    UNCLEAR = "unclear"


_ACCEPT_HINTS = (
    "好的",
    "好哒",
    "好吧",
    "可以",
    "行",
    "嗯嗯",
    "谢谢",
    "按你说的",
    "我就这么做",
    "听你的",
    "采纳",
    "有用",
    "管用",
    "试试看",
)

_REJECT_HINTS = (
    "不行",
    "不好",
    "没用",
    "不对",
    "别瞎说",
    "不采纳",
    "不听",
    "拒绝",
    "太扯",
    "不靠谱",
    "没有用",
    "不认同",
)


def _rule_judge(user_text: str) -> Optional[AcceptanceStatus]:
    """
    关键词启发判定。

    业务逻辑：
    短句且明显接受/拒绝时直接返回；同时命中两边则视为 unclear。
    """
    t = (user_text or "").strip()
    if not t or len(t) > 40:
        return None
    hit_a = any(h in t for h in _ACCEPT_HINTS)
    hit_r = any(h in t for h in _REJECT_HINTS)
    if hit_a and hit_r:
        return AcceptanceStatus.UNCLEAR
    if hit_a and not hit_r:
        return AcceptanceStatus.ACCEPTED
    if hit_r and not hit_a:
        return AcceptanceStatus.REJECTED
    return None


def _parse_status(raw: str) -> Optional[AcceptanceStatus]:
    """从 LLM 文本中解析 status 字段。"""
    text = (raw or "").strip()
    if not text:
        return None
    # 尝试直接 JSON
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            status = str(data.get("status", "")).strip().lower()
            if status in AcceptanceStatus._value2member_map_:
                return AcceptanceStatus(status)
    except json.JSONDecodeError:
        pass
    # 从代码块或夹杂文本中抠 JSON
    match = re.search(r"\{[^{}]*\"status\"[^{}]*\}", text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            status = str(data.get("status", "")).strip().lower()
            if status in AcceptanceStatus._value2member_map_:
                return AcceptanceStatus(status)
        except json.JSONDecodeError:
            pass
    lowered = text.lower()
    if "accepted" in lowered and "rejected" not in lowered:
        return AcceptanceStatus.ACCEPTED
    if "rejected" in lowered and "accepted" not in lowered:
        return AcceptanceStatus.REJECTED
    if "unclear" in lowered:
        return AcceptanceStatus.UNCLEAR
    return None


async def judge_suggestion_acceptance(
    user_text: str,
    suggestion_text: str,
    model_config: Dict[str, Any],
) -> Optional[AcceptanceStatus]:
    """
    判定用户对本轮之前那条建议的态度。

    Args:
        user_text: 本轮 clinic 用户问题
        suggestion_text: 上一条建议全文
        model_config: 与主流程一致的模型配置 dict

    Returns:
        AcceptanceStatus；异常或无法解析时返回 None（可重试）
    """
    # 无建议文本则无法判定
    if not (suggestion_text or "").strip():
        return AcceptanceStatus.UNCLEAR

    ruled = _rule_judge(user_text)
    if ruled is not None:
        return ruled

    system_prompt = """你是对话态度分类器。根据「家长本轮回复」判断其对「上一条闺蜜建议」的态度。
只输出 JSON：{"status":"accepted"|"rejected"|"unclear"}
- accepted：明确采纳、照做、认可有用
- rejected：明确否定、拒绝、认为没用
- unclear：闲聊、换话题、继续提问、态度不明
不要输出其它文字。"""

    user_message = (
        f"上一条建议：\n{(suggestion_text or '')[:800]}\n\n"
        f"家长本轮回复：\n{(user_text or '')[:500]}"
    )

    try:
        cfg = LLMModelConfig(
            provider=model_config.get("provider", "deepseek"),
            name=model_config.get("name", "deepseek-chat"),
            max_in_flight=int(model_config.get("max_in_flight") or 3),
        )
        resp = await llm_client.invoke(
            messages=[{"role": "user", "content": user_message}],
            model_config=cfg,
            system_prompt=system_prompt,
        )
        status = _parse_status(resp.content or "")
        if status is None:
            logger.warning("隐式采纳判定无法解析 LLM 输出，视为失败可重试")
            return None
        return status
    except Exception as e:
        logger.error(f"隐式采纳判定失败: {e}", exc_info=True)
        return None


async def apply_flywheel_for_status(
    status: AcceptanceStatus,
    knowledge_ids: list,
) -> None:
    """
    按三态更新知识质量分。

    业务逻辑：
    accepted → +1；rejected → -1；unclear → 不改分。
    对每个 knowledge_id 调用 vector_store.update_quality_score。
    """
    if status == AcceptanceStatus.UNCLEAR:
        return
    if not knowledge_ids:
        return
    from app.shared.vector_store import vector_store

    feedback = 1 if status == AcceptanceStatus.ACCEPTED else -1
    for kid in knowledge_ids:
        try:
            vector_store.update_quality_score(str(kid), feedback)
        except Exception as e:
            logger.warning(f"飞轮更新质量分失败 id={kid}: {e}")


async def maybe_apply_implicit_feedback(
    device_no: str,
    user_text: str,
    model_config: Dict[str, Any],
) -> None:
    """
    生成前隐式飞轮（clinic / intent clinic agent 共用）。

    业务逻辑：
    1. 读 companion session 的 last_suggestion
    2. 已 applied 或无文本则跳过
    3. 三态判定成功后调质量分并 mark_feedback_applied
    4. 判定失败返回 None 时不置 applied，便于下次重试

    调用方应自行 try/except，避免飞轮异常中断主流程。
    """
    from app.shared.companion_session import companion_session_store

    session = await companion_session_store.get(device_no)
    sug = session.last_suggestion
    if not sug or sug.feedback_applied:
        return
    if not (sug.text or "").strip():
        return

    status = await judge_suggestion_acceptance(
        user_text=user_text,
        suggestion_text=sug.text,
        model_config=model_config,
    )
    if status is None:
        logger.warning(f"隐式采纳判定失败，本轮跳过飞轮 device_no={device_no}")
        return

    await apply_flywheel_for_status(status, sug.knowledge_ids)
    await companion_session_store.mark_feedback_applied(device_no)
    logger.info(
        f"隐式飞轮完成: device_no={device_no}, status={status.value}, "
        f"answer_id={sug.answer_id}, kids={len(sug.knowledge_ids)}"
    )
