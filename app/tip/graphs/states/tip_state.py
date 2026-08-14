"""
小贴士图的状态定义

业务说明：
Pydantic State；原 model_config 改名为 llm_model。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.shared.schemas.data_requirement import DataRequirement


class TipState(BaseModel):
    """小贴士图状态。"""

    model_config = ConfigDict(extra="ignore")

    event_info: Dict[str, Any] = Field(default_factory=dict)
    device_no: str = ""
    llm_model: Dict[str, Any] = Field(default_factory=dict)
    event_dictionary: List[Dict[str, Any]] = Field(default_factory=list)
    question: str = ""
    chat_context: str = ""
    baby_age_months: Optional[int] = None
    data_requirement: Optional[DataRequirement] = None
    history_events: List[Dict[str, Any]] = Field(default_factory=list)
    knowledge: List[Dict[str, Any]] = Field(default_factory=list)
    baby_profile: Dict[str, Any] = Field(default_factory=dict)
    response: str = ""
