"""
段级备注：Go 反查关键字、明细 LLM 抽取与合并

业务说明：
EVENT miss 后用段核心词调 Go filter；事件已定后小 LLM 抽自由明细。
与 resolve_remark_event 共用近窗/小 limit 语义；禁止常识升格。
"""

from __future__ import annotations

import json
import logging
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from app.feeding.graphs.nodes.prompts.system import SEGMENT_REMARK_EXTRACT_SYSTEM_PROMPT
from app.feeding.services.dim_rule_lexicon import (
    PERIOD_WORDS,
    REMARK_VERBS,
    words_pattern,
)
from app.feeding.services.event_hierarchy import get_event_by_id, is_parent_event
from app.shared.graphs.stream_llm_collect import stream_llm_collect
from app.shared.history_window import enum_to_unix
from app.shared.http_client import http_client
from app.shared.llm_client import llm_model_config_from_mapping

logger = logging.getLogger(__name__)

# 与 resolve_remark_event 一致：近窗小页
_REMARK_RESOLVE_LIMIT = 10

# 剥记录动词，留下专名/明细核心
_VERB_STRIP_RE = re.compile(
    r"^(吃了|喝了|喂了|记了|记录了|记录|吃|喝|喂|换了|换)?"
)
_JSON_BLOCK = re.compile(r"\{[\s\S]*\}")
# 数量/钟点片段粗剥（避免整段当 keyword）
_QTY_SPAN_RE = re.compile(
    r"(?:吃了|喝了|喂了)?\s*\d+\s*(?:毫升|ml|ML|ｍｌ)?"
)
_CLOCK_SPAN_RE = re.compile(
    r"\d{1,2}\s*[:：点]\s*\d{0,2}\s*分?"
)
# 判断是否还有备注明细：时段词、记一笔套话、语气词都不算明细
_PERIOD_WORD_RE = words_pattern(PERIOD_WORDS)
_CREATE_VERB_RE = words_pattern(REMARK_VERBS)
_REMARK_NOISE_RE = re.compile(r"[了啦啊呀哦呢吧\s，,。．.！!？?、]")


def segment_has_remark_detail(
    segment: str,
    event_name: str = "",
    event_span: Optional[Tuple[int, int]] = None,
    remark_view: str = "",
) -> bool:
    """
    去掉事件片段、数量、钟点和记一笔套话后，是否还剩应写入备注的描述。

    事件片段按原文起止删除，不读事件视图整句。套话按备注视图剥离。
    「吃了120配方奶」为否；「有点凉」为是。
    """
    heard = segment or ""
    text = remark_view if remark_view else heard
    span = event_span
    if span and len(text) == len(heard):
        start, end = span
        if 0 <= start < end <= len(text):
            text = text[:start] + text[end:]
    else:
        name = (event_name or "").strip()
        if name:
            text = text.replace(name, "")
    text = _CLOCK_SPAN_RE.sub("", text)
    text = _QTY_SPAN_RE.sub("", text)
    text = _PERIOD_WORD_RE.sub("", text)
    text = _CREATE_VERB_RE.sub("", text)
    text = _REMARK_NOISE_RE.sub("", text)
    return bool(text.strip())


def remark_keyword_from_segment(segment: str) -> str:
    """
    从段文本提取备注反查关键字。

    优先剥钟点/量词/记录动词后的短核心；空则回退原文 strip。
    """
    text = (segment or "").strip()
    if not text:
        return ""
    # 先去掉钟点与数量跨度
    core = _CLOCK_SPAN_RE.sub(" ", text)
    core = _QTY_SPAN_RE.sub(" ", core)
    core = re.sub(r"\s+", "", core)
    core = _VERB_STRIP_RE.sub("", core).strip()
    # 再剥句末「了」
    if core.endswith("了") and len(core) > 1:
        core = core[:-1]
    # 过短或剥空：用原文轻归一
    if not core or len(core) > 40:
        # 长段仍试：去掉逗号后半「这次有点黄」时 EVENT 通常已由前半定事件
        # 此处仅作 miss 反查；取逗号前半优先
        head = re.split(r"[，,。；;]", text)[0].strip()
        head = _VERB_STRIP_RE.sub("", head).strip()
        if head.endswith("了") and len(head) > 1:
            head = head[:-1]
        core = head or text
    return core.strip() or text


# 软候选飞轮 / 确认复述用：剥问法壳，留核词（如「午饭」）
_SOFT_PHRASE_QUERY_RE = re.compile(
    r"接下来|下面|待会|等会|几点钟?|什么时候|还有多久|还要多久|"
    r"大概|预计|上次|上一次|最近一次"
)


def soft_event_phrase_from_segment(segment: str) -> str:
    """
    抽取 EVENT 软确认后写入飞轮的短核词。

    业务说明：
    在 remark 核词基础上再剥预测/查史问法壳，避免整句入飞轮。
    """
    kw = remark_keyword_from_segment(segment)
    if not kw:
        return ""
    t = _SOFT_PHRASE_QUERY_RE.sub("", kw)
    t = _VERB_STRIP_RE.sub("", t).strip()
    if t.endswith("了") and len(t) > 1:
        t = t[:-1]
    t = t.strip()
    if t and len(t) <= 12:
        return t
    if kw and len(kw) <= 12:
        return kw
    return (t or kw)[:12]


def merge_remarks(existing: str, llm_remark: str) -> str:
    """
    合并别名/反查备注与 LLM 明细。

    LLM 空 → 保留已有；已有空 → 用 LLM；不同则中文逗号拼接（去包含重复）。
    """
    a = (existing or "").strip()
    b = (llm_remark or "").strip()
    if not b:
        return a
    if not a:
        return b
    if b in a:
        return a
    if a in b:
        return b
    return f"{a}，{b}"


def _row_event_id(row: Dict[str, Any]) -> str:
    return str(row.get("eventId") or row.get("event_id") or "").strip()


def aggregate_remark_leaves(
    rows: List[Dict[str, Any]],
    full_events: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """按 event_id 聚合备注命中行，只保留字典叶子（非父）。"""
    counts: Counter[str] = Counter()
    for row in rows or []:
        eid = _row_event_id(row)
        if eid:
            counts[eid] += 1
    leaves: List[Dict[str, Any]] = []
    for eid, _ in counts.most_common():
        ev = get_event_by_id(eid, full_events)
        if not ev:
            continue
        if is_parent_event(eid, full_events):
            continue
        leaves.append(ev)
    return leaves


async def filter_history_by_remark(
    device_no: str, keyword: str
) -> List[Dict[str, Any]]:
    """本设备近窗、空 eventIds、小 limit 备注模糊。"""
    start_time, end_time = enum_to_unix("last_30_days")
    return await http_client.get_filtered_history_events(
        device_no=device_no,
        event_ids=None,
        start_time=start_time,
        end_time=end_time,
        limit=_REMARK_RESOLVE_LIMIT,
        remark=keyword,
    )


async def resolve_remark_leaves_cached(
    keyword: str,
    *,
    device_no: str,
    full_events: List[Dict[str, Any]],
    cache: Dict[str, List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """
    带同句短缓存的 Go 备注反查 → 叶子列表。

    cache 由调用方（段循环）持有，避免同 keyword 重复 HTTP。
    """
    kw = (keyword or "").strip()
    if not kw:
        return []
    if kw in cache:
        return cache[kw]
    try:
        rows = await filter_history_by_remark(device_no, kw)
    except Exception as exc:
        logger.warning("段级备注反查失败: keyword=%s err=%s", kw, exc)
        rows = []
    leaves = aggregate_remark_leaves(rows or [], full_events)
    cache[kw] = leaves
    return leaves


def _parse_remark_json(content: str) -> str:
    """解析明细 LLM 的 {\"remark\": \"...\"}。"""
    raw = (content or "").strip()
    if not raw:
        return ""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        m = _JSON_BLOCK.search(raw)
        if not m:
            return ""
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return ""
    if not isinstance(data, dict):
        return ""
    return str(data.get("remark") or "").strip()


async def extract_detail_remark_llm(
    segment: str,
    event_name: str,
    llm_model: Dict[str, Any],
) -> str:
    """
    事件已定后抽取自由明细备注（可空）。

    SSE 路径经 stream_llm_collect 透出 reasoning。
    """
    seg = (segment or "").strip()
    ename = (event_name or "").strip() or "该事件"
    if not seg:
        return ""
    cfg = llm_model_config_from_mapping(llm_model or {})
    user = (
        f"已定事件：{ename}\n"
        f"用户段原文：{seg}\n"
        "请抽取应写入历史备注的明细（无则 remark 为空字符串）。"
    )
    content = await stream_llm_collect(
        messages=[{"role": "user", "content": user}],
        model_config=cfg,
        system_prompt=SEGMENT_REMARK_EXTRACT_SYSTEM_PROMPT,
        node_name="resolve_segments_remark",
    )
    return _parse_remark_json(content or "")
