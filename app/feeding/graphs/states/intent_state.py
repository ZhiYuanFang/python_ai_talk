"""
意图分析图的状态定义

业务说明：
Pydantic State，路由构造赋值；节点返回字段补丁合并。
原 TypedDict 字段 model_config 与 Pydantic 保留名冲突，改名为 llm_model。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.feeding.schemas.intent_result import IntentResult
from app.shared.schemas.data_requirement import DataRequirement


class IntentState(BaseModel):
    """意图分析图状态。"""

    model_config = ConfigDict(extra="ignore")

    user_input: str = ""
    device_no: str = ""
    # 原 state["model_config"]；避免与 BaseModel.model_config 撞名
    llm_model: Dict[str, Any] = Field(default_factory=dict)

    event_dictionary: List[Dict[str, Any]] = Field(default_factory=list)
    event_dictionary_full: List[Dict[str, Any]] = Field(default_factory=list)
    intent_result: Optional[IntentResult] = None
    data_requirement: Optional[DataRequirement] = None
    history_events: List[Dict[str, Any]] = Field(default_factory=list)
    knowledge: List[Dict[str, Any]] = Field(default_factory=list)
    baby_profile: Dict[str, Any] = Field(default_factory=dict)
    response: str = ""

    match_confidence: Optional[float] = None
    match_source: Optional[str] = None
    matched_vector_id: str = ""
    intent_cache_hit: bool = False

    need_confirm: bool = False
    confirm_type: str = ""
    confirm_message: str = ""
    conversation_id: str = ""
    in_progress_hint: str = ""
    remark_keyword: str = ""

    should_update_vector: bool = False
    feedback_recorded: bool = False
