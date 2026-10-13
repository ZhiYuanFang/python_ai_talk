"""
维判定统一入口

业务说明：
各飞轮维共用同一判定形状（方法复用，非 chroma 基建复用）：
  ① 可选强规则 → ② 整段飞轮命中跳过 LLM → ③ 维小 LLM
  → ④ 成功则以段整句回写 → ⑤ 失败/缺槽不写飞轮。
时间维：规则（调用方）→ 相对配方飞轮物化 → TIME LLM → 合法配方回写 + rule_gap。
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional, Tuple

from app.feeding.services.locate_cue_store import (
    LOCATE_STRATEGIES,
    locate_cue_store,
)
from app.feeding.services.predict_cue_store import predict_cue_store
from app.feeding.services.read_source_cue_store import read_source_cue_store
from app.feeding.services.rule_gap_store import rule_gap_store
from app.feeding.services.segment_dim_llm import llm_resolve_time
from app.feeding.services.time_cue_store import time_cue_store
from app.feeding.services.time_formula import materialize_time_formula
from app.shared.graphs.stream_llm_collect import stream_llm_collect
from app.shared.llm_client import llm_model_config_from_mapping

logger = logging.getLogger(__name__)

_JSON_BLOCK = re.compile(r"\{[\s\S]*\}")


def _parse_json_obj(content: str) -> Dict[str, Any]:
    """从 LLM 正文解析 JSON 对象。"""
    raw = (content or "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        m = _JSON_BLOCK.search(raw)
        if not m:
            return {}
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return {}
    return data if isinstance(data, dict) else {}


async def resolve_read_source(
    segment: str,
    *,
    llm_model: Optional[Dict[str, Any]] = None,
    allow_llm: bool = True,
) -> Tuple[Optional[str], bool]:
    """
    R·source 维：整段飞轮 →（可选）并入 OP LLM 时由调用方补。

    本函数仅做飞轮热路径；缺维时返回 (None, False) 由 OP 冷路径补齐并回写。

    Returns:
        (record|predict|None, from_flywheel)
    """
    text = (segment or "").strip()
    if not text:
        return None, False
    hit = read_source_cue_store.search_read_source(text)
    if hit in ("record", "predict"):
        return hit, True
    # 本维不单独打 LLM（与 OP 冷路径合并，避免双次调用）；allow_llm 预留
    _ = (llm_model, allow_llm)
    return None, False


async def resolve_predict_dims(
    segment: str,
    *,
    llm_model: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str, bool]:
    """
    R·predict 两维：整段飞轮 → 预测维小 LLM → 整段回写。

    Returns:
        (predict_channel, time_answer, need_confirm)
    """
    text = (segment or "").strip()
    if not text:
        return "", "", True
    hit = predict_cue_store.search_dims(text)
    if hit:
        return hit[0], hit[1], False

    cfg = llm_model_config_from_mapping(llm_model or {})
    # 复用 OP 提示中的预测两维约束，缩小 user 任务
    content = await stream_llm_collect(
        messages=[
            {
                "role": "user",
                "content": (
                    "本段已是预测问答。只输出 JSON："
                    '{"predict_channel":"active|next","time_answer":"clock|remain",'
                    '"need_confirm":false}\n'
                    f"段原文：{text}"
                ),
            }
        ],
        model_config=cfg,
        system_prompt=(
            "你是宝宝照护记录「预测两维」助手。只输出 JSON，不要 markdown。\n"
            "领域含喂养、睡眠、换尿布、营养品、疫苗等可落库事件（以事件表为准）。\n"
            "predict_channel 只能 active|next；time_answer 只能 clock|remain。\n"
            "还有多久醒来/几点醒 → active+remain 或 active+clock；"
            "还有多久睡觉 → next+remain 或 next+clock。\n"
            "内部思考（reasoning）须使用中文。"
        ),
        node_name="segment_predict_dims_llm",
    )
    data = _parse_json_obj(content or "")
    pc = str(data.get("predict_channel") or "").strip().lower()
    ta = str(data.get("time_answer") or "").strip().lower()
    need_confirm = bool(data.get("need_confirm"))
    if pc not in ("active", "next") or ta not in ("clock", "remain"):
        return "", "", True
    if not need_confirm:
        predict_cue_store.add(text, pc, ta)
    return pc, ta, need_confirm


async def resolve_time(
    segment: str,
    *,
    utterance: str = "",
    device_no: str = "",
    llm_model: Optional[Dict[str, Any]] = None,
    reason: str = "time_llm",
    allow_flywheel: bool = True,
) -> Tuple[Optional[int], Optional[int], str]:
    """
    时间维（规则已 miss 后）：飞轮物化 → TIME LLM → 合法配方回写。

    业务说明：
    调用方须先跑本地规则；本函数不重复规则。
    allow_flywheel=False 时（如 read 轨）跳过飞轮读写，仍可 LLM + rule_gap。

    Returns:
        (start_unix, end_unix, source)；source 为 flywheel|llm|none
        open_start 时 end_unix 可为 0。
    """
    text = (segment or "").strip()
    if not text:
        return None, None, "none"

    if allow_flywheel:
        formula = time_cue_store.search_formula(text)
        if formula is not None:
            matured = materialize_time_formula(formula)
            if matured is not None:
                st, et = matured
                if st and st > 0:
                    return st, et, "flywheel"

    try:
        st, et, formula, summary = await llm_resolve_time(text, llm_model or {})
    except Exception as exc:
        logger.warning("TIME 小 LLM 失败: %s", exc)
        rule_gap_store.record(
            dimension="time",
            segment_text=text,
            utterance=utterance or text,
            reason=f"{reason}_llm_fail",
            llm_used=True,
            llm_result=str(exc)[:200],
            device_no=device_no,
        )
        return None, None, "none"

    rule_gap_store.record(
        dimension="time",
        segment_text=text,
        utterance=utterance or text,
        reason=reason,
        llm_used=True,
        llm_result=summary,
        device_no=device_no,
    )
    if st is None or st <= 0:
        return None, None, "none"
    if allow_flywheel and formula is not None:
        time_cue_store.add(text, formula)
    return st, int(et if et is not None else st), "llm"


async def resolve_locate(
    segment: str,
    *,
    llm_model: Optional[Dict[str, Any]] = None,
    default_strategy: str = "latest",
) -> Tuple[str, bool]:
    """
    U/D 定位策略：整段飞轮 → 小 LLM → 整段回写。

    Returns:
        (strategy_code, need_confirm)；strategy 不含 historyId
    """
    text = (segment or "").strip()
    if not text:
        return default_strategy, True
    hit = locate_cue_store.search_strategy(text)
    if hit:
        return hit, False

    cfg = llm_model_config_from_mapping(llm_model or {})
    content = await stream_llm_collect(
        messages=[
            {
                "role": "user",
                "content": f"段原文：{text}",
            }
        ],
        model_config=cfg,
        system_prompt=(
            "你是宝宝照护记录「改删定位策略」助手。只输出 JSON，不要 markdown。\n"
            "领域含喂养、睡眠、换尿布、营养品、疫苗等可落库事件（以事件表为准）。\n"
            "strategy 只能是：latest（最近一条）、open_timer（仅进行中计时）、"
            "prefer_completed（优先已完成）。\n"
            "禁止输出 historyId。内部思考（reasoning）须使用中文。\n"
            'JSON：{"strategy":"latest","need_confirm":false}'
        ),
        node_name="segment_locate_llm",
    )
    data = _parse_json_obj(content or "")
    st = str(data.get("strategy") or "").strip().lower()
    need_confirm = bool(data.get("need_confirm"))
    if st not in LOCATE_STRATEGIES:
        return default_strategy, True
    if not need_confirm:
        locate_cue_store.add(text, st)
    return st, need_confirm
