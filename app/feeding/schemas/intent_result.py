"""
意图图内 IntentResult 模型

业务说明：
分类 / 备注反查 / 确认管线的主路径载体，替代无模式 Dict[str, Any]。
与对外 IntentResponse 字段对齐，但不替代 API schema。
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from pydantic import BaseModel, ConfigDict, Field


class IntentEventItem(BaseModel):
    """多事件子项。"""

    model_config = ConfigDict(extra="ignore")

    action: str = ""
    event_name: str = ""
    event_id: str = ""
    quantity: Optional[int] = None


class IntentResult(BaseModel):
    """
    意图分析结果（图内）。

    业务说明：
    LLM JSON 经 model_validate 进入；规则节点用属性读写。
    """

    model_config = ConfigDict(extra="ignore")

    target_type: str = "conversation"
    action: str = "reply"
    op: str = ""
    event_name: str = ""
    event_id: str = ""
    event_ids: List[str] = Field(default_factory=list)
    events: List[IntentEventItem] = Field(default_factory=list)
    quantity: Optional[int] = None
    event_type: Optional[str] = None
    event_unit: Optional[Any] = None
    is_new_event: bool = False
    remark_keyword: str = ""
    missing_events: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    content: str = ""
    start_time: Optional[int] = None
    end_time: Optional[int] = None
    time_range: Optional[str] = None
    limit: Optional[int] = None
    history_mode: Optional[str] = None
    match_source: Optional[str] = None
    match_confidence: Optional[float] = None
    need_confirm: Optional[bool] = None
    confirm_type: Optional[str] = None
    confirm_message: str = ""
    conversation_id: Optional[str] = None
    options: List[Dict[str, Any]] = Field(default_factory=list)

    def to_plain_dict(self) -> Dict[str, Any]:
        """管线/响应组装用字典（排除纯 None 可选时可再筛）。"""
        return self.model_dump(exclude_none=False)


# IntentResult 中「非 Optional、默认空串」的字段：旧管线/LLM 常写 null，校验前需收成 ""
_INTENT_RESULT_EMPTY_STR_FIELDS = (
    "target_type",
    "action",
    "op",
    "event_name",
    "event_id",
    "remark_keyword",
    "content",
    "confirm_message",
)


def coerce_intent_result(value: Any) -> IntentResult:
    """
    图内 intent_result 归一：None / dict / IntentResult → IntentResult。

    业务说明：节点读 state、路由读 op 时统一入口，避免主路径混用 .get 与属性。
    字典入参里默认空串字段若为 None（如确认清态写 confirm_message: null），先归一为 ""，
    再 model_validate，避免 Pydantic 拒收导致确认后续聊 500。
    """
    if value is None:
        return IntentResult()
    if isinstance(value, IntentResult):
        return value
    if isinstance(value, Mapping):
        data = dict(value)
        for key in _INTENT_RESULT_EMPTY_STR_FIELDS:
            if key in data and data[key] is None:
                data[key] = ""
        return IntentResult.model_validate(data)
    raise TypeError(f"无法转为 IntentResult: {type(value)!r}")
