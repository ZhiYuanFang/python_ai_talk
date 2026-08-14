"""
护理留意图状态

业务说明：
Pydantic State；复用 tip/clinic 共享字段；items 钉为 DTO。
原 model_config 改名为 llm_model。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from app.care_alert.schemas.care_alert import CareAlertItemDto
from app.shared.schemas.data_requirement import DataRequirement


class CareAlertState(BaseModel):
    """护理留意图状态。"""

    model_config = ConfigDict(extra="ignore")

    device_no: str = ""
    day: str = ""
    llm_model: Dict[str, Any] = Field(default_factory=dict)
    data_requirement: Optional[DataRequirement] = None
    baby_age_months: Optional[int] = None
    history_events: List[Dict[str, Any]] = Field(default_factory=list)
    baby_profile: Dict[str, Any] = Field(default_factory=dict)
    history_summary: Any = None
    kg_context: Any = None
    items: List[Union[CareAlertItemDto, Dict[str, Any]]] = Field(default_factory=list)
