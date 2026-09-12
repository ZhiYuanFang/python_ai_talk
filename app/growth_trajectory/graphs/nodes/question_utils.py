"""
问题 payload 规范化与 LLM JSON 辅助

业务说明：
choice 必须恰好 2 选项；供 interrupt 前后与 SSE question 事件复用。
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict, List, Optional

from app.shared.graphs.state_patch import state_get
from app.shared.llm_client import llm_client, llm_model_config_from_mapping
from app.shared.llm_json import loads_llm_json

logger = logging.getLogger(__name__)


def extract_json_object(raw: str) -> Optional[Dict[str, Any]]:
    """从 LLM 原文解析顶层 JSON 对象。"""
    try:
        data = loads_llm_json(raw)
    except (json.JSONDecodeError, ValueError, TypeError):
        logger.warning("成长轨迹 JSON 解析失败")
        return None
    if isinstance(data, dict):
        return data
    return None


def normalize_question_payload(
    raw: Any,
    *,
    default_id: str = "",
    default_prompt: str = "请补充一点近期情况",
    prefer_choice: bool = True,
) -> Dict[str, Any]:
    """
    规范为 interrupt / SSE 用问题 dict。

    Returns:
        {id, prompt, format, choices}；choice 时 choices 恰好 2 个。
    """
    data = raw if isinstance(raw, dict) else {}
    qid = str(data.get("id") or data.get("question_id") or default_id or "").strip()
    if not qid:
        qid = f"q_{uuid.uuid4().hex[:8]}"
    prompt = str(data.get("prompt") or data.get("question") or default_prompt).strip()
    fmt = str(data.get("format") or "").strip().lower()
    choices_raw = data.get("choices")
    choices: List[str] = []
    if isinstance(choices_raw, list):
        for c in choices_raw:
            s = str(c).strip() if c is not None else ""
            if s:
                choices.append(s)

    if fmt not in ("choice", "free_text"):
        fmt = "choice" if (prefer_choice or len(choices) >= 2) else "free_text"

    if fmt == "choice":
        # 契约：必须恰好 2 个选项
        if len(choices) >= 2:
            choices = choices[:2]
        elif len(choices) == 1:
            choices = [choices[0], "其他 / 再说一下"]
        else:
            choices = ["是的", "不是"]
    else:
        choices = []

    return {
        "id": qid,
        "prompt": prompt or default_prompt,
        "format": fmt,
        "choices": choices,
    }


def interrupt_value_to_answer(resume_value: Any, question: Dict[str, Any]) -> Dict[str, Any]:
    """将 Command(resume=...) 的值规范为问答记录。"""
    qid = str(question.get("id") or "")
    if isinstance(resume_value, dict):
        value = resume_value.get("value")
        if value is None:
            value = resume_value.get("answer") or resume_value.get("text") or ""
        rid = str(
            resume_value.get("question_id")
            or resume_value.get("questionId")
            or resume_value.get("id")
            or qid
        )
        return {
            "question_id": rid,
            "prompt": question.get("prompt") or "",
            "format": question.get("format") or "",
            "choices": question.get("choices") or [],
            "value": str(value).strip() if value is not None else "",
        }
    return {
        "question_id": qid,
        "prompt": question.get("prompt") or "",
        "format": question.get("format") or "",
        "choices": question.get("choices") or [],
        "value": str(resume_value).strip() if resume_value is not None else "",
    }


async def invoke_llm_json(
    state: Any,
    *,
    system_prompt: str,
    user_message: str,
) -> Optional[Dict[str, Any]]:
    """调用 LLM 并解析 JSON；失败返回 None。"""
    model_config = llm_model_config_from_mapping(
        state_get(state, "llm_model") or state_get(state, "model_config")
    )
    if model_config is None:
        logger.warning("成长轨迹缺 model，跳过 LLM")
        return None
    try:
        resp = await llm_client.invoke(
            messages=[{"role": "user", "content": user_message}],
            model_config=model_config,
            system_prompt=system_prompt,
        )
        raw = (resp.content or "").strip()
        return extract_json_object(raw)
    except Exception as e:
        logger.warning("成长轨迹 LLM 调用失败: %s", e, exc_info=True)
        return None


async def invoke_llm_text(
    state: Any,
    *,
    system_prompt: str,
    user_message: str,
) -> str:
    """调用 LLM 取纯文本；失败返回空串。"""
    model_config = llm_model_config_from_mapping(
        state_get(state, "llm_model") or state_get(state, "model_config")
    )
    if model_config is None:
        logger.warning("成长轨迹缺 model，跳过 LLM 文本生成")
        return ""
    try:
        resp = await llm_client.invoke(
            messages=[{"role": "user", "content": user_message}],
            model_config=model_config,
            system_prompt=system_prompt,
        )
        return (resp.content or "").strip()
    except Exception as e:
        logger.warning("成长轨迹 LLM 文本失败: %s", e, exc_info=True)
        return ""
