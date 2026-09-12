"""
成长轨迹 turn 请求/事件契约

业务说明：
对齐 openspec CONTRACT：Go→Python POST /v1/growth-trajectory/turn。
字段以 snake_case 为权威；过渡双收 camelCase。
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from app.feeding.schemas.intent import ModelConfig


class GrowthTrajectoryAnswer(BaseModel):
    """用户对某一问的作答。"""

    model_config = ConfigDict(populate_by_name=True)

    question_id: str = Field(
        "",
        validation_alias=AliasChoices("question_id", "questionId"),
        description="问题 id",
    )
    value: str = Field("", description="选项文案或自由文本")


class GrowthTrajectoryTurnRequest(BaseModel):
    """
    成长轨迹一轮 SSE 请求。

    action=start|answer|restart；answer 仅 answer 时需要。
    """

    model_config = ConfigDict(populate_by_name=True)

    device_no: str = Field(
        ...,
        validation_alias=AliasChoices("device_no", "deviceNo"),
        description="设备号",
    )
    session_id: Optional[str] = Field(
        None,
        validation_alias=AliasChoices("session_id", "sessionId"),
        description="会话/thread_id；start 可空，answer 必填",
    )
    action: Literal["start", "answer", "restart"] = Field(
        ...,
        description="start|answer|restart",
    )
    answer: Optional[GrowthTrajectoryAnswer] = Field(
        None,
        description="answer 动作时的作答",
    )
    prior_feedback: List[Any] = Field(
        default_factory=list,
        validation_alias=AliasChoices("prior_feedback", "priorFeedback"),
        description="历史反馈（Go 注入）；有则先 confirm_prior",
    )
    horizon_days: int = Field(
        7,
        validation_alias=AliasChoices("horizon_days", "horizonDays"),
        description="预测天数，默认 7",
    )
    model: Optional[Union[str, ModelConfig, Dict[str, Any]]] = Field(
        None,
        description="可选 LLM 配置；缺省用内置默认",
    )
