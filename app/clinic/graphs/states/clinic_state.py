"""
诊疗图的状态定义

业务说明：
Pydantic State；原 model_config 字段改名为 llm_model。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.shared.schemas.data_requirement import DataRequirement


class ClinicState(BaseModel):
    """clinic_graph 执行过程中的状态数据。"""

    model_config = ConfigDict(extra="ignore")

    question: str = ""
    device_no: str = ""
    llm_model: Dict[str, Any] = Field(default_factory=dict)
    event_dictionary: List[Dict[str, Any]] = Field(default_factory=list)
    chat_context: str = ""
    skip_knowledge: bool = False
    force_needs_history: bool = False
    block_fast_path: bool = False

    needs_history: bool = False
    data_requirement: Optional[DataRequirement] = None
    history_events: List[Dict[str, Any]] = Field(default_factory=list)
    knowledge: List[Dict[str, Any]] = Field(default_factory=list)
    baby_profile: Dict[str, Any] = Field(default_factory=dict)
    baby_age_months: Optional[int] = None
    age_band: Optional[str] = None
    standalone_question: Optional[str] = None
    qa_rewrite_miss_reason: str = ""
    qa_hit: bool = False
    qa_answer: str = ""
    qa_miss_reason: str = ""
    qa_match_id: str = ""
    qa_match_score: float = 0.0
