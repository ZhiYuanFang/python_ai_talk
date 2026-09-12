"""
成长轨迹图状态

业务说明：
承载多轮 interrupt 会话字段：画像/弱史、确认、结构化轮次、待问、Markdown 结果。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.shared.schemas.data_requirement import DataRequirement


class GrowthTrajectoryState(BaseModel):
    """成长轨迹预测图状态。"""

    model_config = ConfigDict(extra="ignore")

    # 会话与请求
    device_no: str = ""
    session_id: str = ""
    horizon_days: int = 7
    llm_model: Dict[str, Any] = Field(default_factory=dict)

    # 历史反馈（confirm_prior 用，不计入 structured_round）
    prior_feedback: List[Any] = Field(default_factory=list)
    confirmed_prior: bool = False

    # 问答累积与轮次
    qa_so_far: List[Dict[str, Any]] = Field(default_factory=list)
    structured_round: int = 0
    max_structured_rounds: int = 6
    final_ask_done: bool = False

    # 规划与待问
    plan_decision: str = ""  # enough | ask | reconfirm | final_ask | generate
    pending_question: Optional[Dict[str, Any]] = None
    phase: str = "init"

    # 画像与弱喂养史
    needs_history: bool = True
    data_requirement: Optional[DataRequirement] = None
    history_events: List[Dict[str, Any]] = Field(default_factory=list)
    baby_profile: Dict[str, Any] = Field(default_factory=dict)
    baby_age_months: Optional[int] = None

    # 最终产物
    result_markdown: str = ""
