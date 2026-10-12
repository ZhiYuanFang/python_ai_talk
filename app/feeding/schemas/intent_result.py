"""
意图图内 IntentResult 模型

业务说明：
分类 / 备注反查 / 确认管线的主路径载体，替代无模式 Dict[str, Any]。
CRUD/读权威在 events[].op；无顶层 op/action。
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from pydantic import BaseModel, ConfigDict, Field


class IntentEventItem(BaseModel):
    """
    多事件子项。

    业务说明：
    op 为 create|update|delete|end|read；action 可选（start|one|end）。
    查记录与 create 明细备注均用 remark（与 Go batch/filter 一致）。
    ignore_time_range：op=read 时由分类判定「上一次」类点查是否忽略时间窗。
    """

    model_config = ConfigDict(extra="ignore")

    op: str = ""
    action: str = ""
    event_name: str = ""
    event_id: str = ""
    quantity: Optional[int] = None
    history_id: Optional[int] = None
    remark: Optional[str] = None
    start_time: Optional[int] = None
    end_time: Optional[int] = None
    # 点查「上一次」为 true → 拉史透传 ignoreTimeRange；缺省 false
    ignore_time_range: bool = False
    # 段级多维：缺 quantity / 段原文（写短说法用）
    missing_quantity: bool = False
    segment_text: str = ""


class IntentResult(BaseModel):
    """
    意图分析结果（图内）。

    业务说明：
    LLM JSON 经归一与 model_validate 进入；规则节点用属性读写。
    """

    model_config = ConfigDict(extra="ignore")

    # 权威六轨 create|read|update|delete|exit|other（遗留值经 normalize）
    target_type: str = "other"
    event_name: str = ""
    event_id: str = ""
    event_ids: List[str] = Field(default_factory=list)
    events: List[IntentEventItem] = Field(default_factory=list)
    quantity: Optional[int] = None
    event_type: Optional[str] = None
    event_unit: Optional[Any] = None
    is_new_event: bool = False
    remark: str = ""
    missing_events: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    content: str = ""
    start_time: Optional[int] = None
    end_time: Optional[int] = None
    time_range: Optional[str] = None
    limit: Optional[int] = None
    history_mode: Optional[str] = None
    # R 子维：仅 target_type=read 时 record|predict
    read_source: Optional[str] = None
    # 预测问答分维：仅 read+predict（或遗留 predict）时有效
    predict_channel: Optional[str] = None
    time_answer: Optional[str] = None
    match_source: Optional[str] = None
    match_confidence: Optional[float] = None
    need_confirm: Optional[bool] = None
    confirm_type: Optional[str] = None
    confirm_message: str = ""
    conversation_id: Optional[str] = None
    options: List[Dict[str, Any]] = Field(default_factory=list)
    # 段多维：分句/事件失败引导重说；number 叶缺量
    segment_failed: bool = False
    missing_quantity: bool = False

    def to_plain_dict(self) -> Dict[str, Any]:
        """管线/响应组装用字典。"""
        return self.model_dump(exclude_none=False)


# 默认空串字段：旧管线/LLM 常写 null
_INTENT_RESULT_EMPTY_STR_FIELDS = (
    "target_type",
    "event_name",
    "event_id",
    "remark",
    "content",
    "confirm_message",
)


def coerce_intent_result(value: Any) -> IntentResult:
    """
    图内 intent_result 归一：None / dict / IntentResult → IntentResult。

    业务说明：先投影旧顶层 op/action 进 events，再校验；
    字符串默认字段的 None 收成 ""。
    """
    if value is None:
        return IntentResult()
    if isinstance(value, IntentResult):
        return value
    if isinstance(value, Mapping):
        from app.feeding.services.intent_events import normalize_intent_events

        data = normalize_intent_events(dict(value))
        for key in _INTENT_RESULT_EMPTY_STR_FIELDS:
            if key in data and data[key] is None:
                data[key] = ""
        # 子项 confirm 无关字段里的 None op 已由 normalize 处理
        for ev in data.get("events") or []:
            if isinstance(ev, dict) and ev.get("op") is None:
                ev["op"] = ""
            if isinstance(ev, dict) and ev.get("action") is None:
                ev["action"] = ""
            if isinstance(ev, dict) and ev.get("event_name") is None:
                ev["event_name"] = ""
            if isinstance(ev, dict) and ev.get("event_id") is None:
                ev["event_id"] = ""
        return IntentResult.model_validate(data)
    raise TypeError(f"无法转为 IntentResult: {type(value)!r}")
