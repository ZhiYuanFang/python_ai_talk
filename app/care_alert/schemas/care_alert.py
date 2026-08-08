"""
护理留意分析请求与响应模型

业务说明：
与 Go 编排 / Flutter CareAlertEventItem DTO 对齐。
内部契约以 snake_case 为权威；过渡双收 camelCase（deviceNo 等）。
响应序列化使用 camelCase，便于 Go 透传 Flutter。

设计思路：
1. model 支持字符串 deepseek|zhipu，或完整 {provider,name,max_in_flight}
2. suggestionId 可由 Python 生成 UUID；Go 亦可覆盖后写入日缓存
3. reasons 字段与 design D3 / Flutter parseCareAlertReason 一致（毫秒）
"""

from __future__ import annotations

from typing import Annotated, Any, Dict, List, Optional, Union

from pydantic import (
    AliasChoices,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    field_validator,
)

from app.feeding.schemas.intent import ModelConfig


def _coerce_optional_str(value: Any) -> Optional[str]:
    """将入站值规范为可选字符串。"""
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


class CareAlertReasonDto(BaseModel):
    """
    单条结构化原因（非医疗诊断）

    业务说明：
    type 常用 elongatedInterval / longActive / suddenAbsence；未知 type 仍保留原文字符串。
    """

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    type: str = Field(..., description="原因类型字符串")
    score: float = Field(0.0, description="相对分数，越高越值得留意")
    expectation_used: bool = Field(
        False,
        validation_alias=AliasChoices("expectation_used", "expectationUsed"),
        serialization_alias="expectationUsed",
        description="是否使用了月龄期望基准",
    )
    age_months: Optional[int] = Field(
        None,
        validation_alias=AliasChoices("age_months", "ageMonths"),
        serialization_alias="ageMonths",
    )
    median_gap_ms: Optional[int] = Field(
        None,
        validation_alias=AliasChoices("median_gap_ms", "medianGapMs"),
        serialization_alias="medianGapMs",
    )
    last_gap_ms: Optional[int] = Field(
        None,
        validation_alias=AliasChoices("last_gap_ms", "lastGapMs"),
        serialization_alias="lastGapMs",
    )
    expect_gap_max_ms: Optional[int] = Field(
        None,
        validation_alias=AliasChoices("expect_gap_max_ms", "expectGapMaxMs"),
        serialization_alias="expectGapMaxMs",
    )
    p75_dur_ms: Optional[int] = Field(
        None,
        validation_alias=AliasChoices("p75_dur_ms", "p75DurMs"),
        serialization_alias="p75DurMs",
    )
    elapsed_ms: Optional[int] = Field(
        None,
        validation_alias=AliasChoices("elapsed_ms", "elapsedMs"),
        serialization_alias="elapsedMs",
    )
    expect_dur_max_ms: Optional[int] = Field(
        None,
        validation_alias=AliasChoices("expect_dur_max_ms", "expectDurMaxMs"),
        serialization_alias="expectDurMaxMs",
    )
    daily_avg: Optional[float] = Field(
        None,
        validation_alias=AliasChoices("daily_avg", "dailyAvg"),
        serialization_alias="dailyAvg",
    )
    recent_48h_count: Optional[int] = Field(
        None,
        validation_alias=AliasChoices("recent_48h_count", "recent48hCount"),
        serialization_alias="recent48hCount",
    )
    still_expected: Optional[bool] = Field(
        None,
        validation_alias=AliasChoices("still_expected", "stillExpected"),
        serialization_alias="stillExpected",
    )
    detail_lines: List[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("detail_lines", "detailLines"),
        serialization_alias="detailLines",
        description="可选中文补充说明行",
    )


class CareAlertItemDto(BaseModel):
    """
    按事件聚合的留意项（跑马灯一行 / 详情全量原因）

    业务说明：
    followUpPrompt 必须可原样注入陪伴树洞；语气「值得留意」非诊断。
    """

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    suggestion_id: Optional[str] = Field(
        None,
        validation_alias=AliasChoices("suggestion_id", "suggestionId"),
        serialization_alias="suggestionId",
        description="当日作用域 UUID；可选，缺省由服务填充",
    )
    event_id: str = Field(
        ...,
        validation_alias=AliasChoices("event_id", "eventId"),
        serialization_alias="eventId",
    )
    event_name: str = Field(
        ...,
        validation_alias=AliasChoices("event_name", "eventName"),
        serialization_alias="eventName",
    )
    summary_line: str = Field(
        ...,
        validation_alias=AliasChoices("summary_line", "summaryLine"),
        serialization_alias="summaryLine",
        description="跑马灯单行摘要",
    )
    follow_up_prompt: str = Field(
        ...,
        validation_alias=AliasChoices("follow_up_prompt", "followUpPrompt"),
        serialization_alias="followUpPrompt",
        description="家长可直接发给树洞的追问原文",
    )
    reasons: List[CareAlertReasonDto] = Field(default_factory=list)


class CareAlertAnalyzeResponse(BaseModel):
    """分析接口响应：items 列表驱动跑马灯。"""

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    items: List[CareAlertItemDto] = Field(default_factory=list)


def _normalize_model_field(value: Any) -> Union[str, ModelConfig, Dict[str, Any]]:
    """
    规范 model 字段：允许字符串提供商或完整 ModelConfig。

    业务逻辑：
    - "deepseek" / "zhipu" / "glm" → 原样字符串（服务层再补默认模型名）
    - dict / ModelConfig → 交给 ModelConfig 校验
    """
    if isinstance(value, ModelConfig):
        return value
    if isinstance(value, str):
        return value.strip().lower()
    if isinstance(value, dict):
        return value
    raise TypeError("model 须为 deepseek|zhipu 字符串或 {provider,name,...} 对象")


class CareAlertAnalyzeRequest(BaseModel):
    """
    Go → Python 护理留意分析请求

    业务说明：
    Go 传入设备、逻辑日、模型标识；可选透传月龄/历史摘要/KG 上下文。
    未透传时由本仓按 tip 同源节点拉取历史、画像与向量知识。
    """

    model_config = ConfigDict(populate_by_name=True)

    device_no: Annotated[
        str,
        Field(
            validation_alias=AliasChoices("device_no", "deviceNo"),
            description="设备编号（宝宝维度）",
        ),
    ]
    day: Annotated[
        Optional[str],
        BeforeValidator(_coerce_optional_str),
        Field(
            default=None,
            description="逻辑日 YYYY-MM-DD（Asia/Shanghai）；可选，仅日志/上下文",
        ),
    ] = None
    # 字符串 deepseek|zhipu，或完整模型配置
    model: Annotated[
        Union[str, ModelConfig, Dict[str, Any]],
        BeforeValidator(_normalize_model_field),
        Field(..., description="模型：deepseek|zhipu 或完整 ModelConfig"),
    ]
    age_months: Optional[int] = Field(
        None,
        validation_alias=AliasChoices("age_months", "ageMonths"),
        description="可选月龄；缺省由画像派生",
    )
    history_summary: Optional[Any] = Field(
        None,
        validation_alias=AliasChoices("history_summary", "historySummary"),
        description="可选预拼历史；空则本仓拉取",
    )
    kg_context: Optional[Any] = Field(
        None,
        validation_alias=AliasChoices("kg_context", "kgContext"),
        description="可选预拼知识；空则本仓向量检索",
    )

    @field_validator("device_no")
    @classmethod
    def _device_no_non_empty(cls, v: str) -> str:
        """设备号去空白后不得为空。"""
        s = (v or "").strip()
        if not s:
            raise ValueError("device_no 不能为空")
        return s


class CareAlertFeedbackRequest(BaseModel):
    """
    Go → Python 固定意图通识飞轮（无 NLP）

    业务说明：
    仅接受 ignore|follow_up；按 suggestion_id 映射更新通识质量分。
    Go 在本接口失败时仍对客户端返回成功（best-effort）。
    """

    model_config = ConfigDict(populate_by_name=True)

    device_no: Annotated[
        str,
        Field(
            validation_alias=AliasChoices("device_no", "deviceNo"),
            description="设备编号（宝宝维度）",
        ),
    ]
    suggestion_id: Annotated[
        str,
        Field(
            validation_alias=AliasChoices("suggestion_id", "suggestionId"),
            description="当日缓存项 UUID",
        ),
    ]
    intent: Annotated[
        str,
        Field(..., description="固定意图：ignore|follow_up"),
    ]
    day: Annotated[
        Optional[str],
        BeforeValidator(_coerce_optional_str),
        Field(default=None, description="逻辑日 YYYY-MM-DD（Asia/Shanghai）"),
    ] = None

    @field_validator("device_no", "suggestion_id")
    @classmethod
    def _non_empty_id(cls, v: str) -> str:
        """device_no / suggestion_id 去空白后不得为空。"""
        s = (v or "").strip()
        if not s:
            raise ValueError("字段不能为空")
        return s

    @field_validator("intent")
    @classmethod
    def _intent_fixed(cls, v: str) -> str:
        """仅允许固定意图枚举。"""
        s = (v or "").strip()
        if s not in ("ignore", "follow_up"):
            raise ValueError("intent 必须为 ignore 或 follow_up")
        return s


class CareAlertFeedbackResponse(BaseModel):
    """飞轮 ACK（HTTP 200 + ok=true；质量更新为 best-effort 副作用）。"""

    model_config = ConfigDict(populate_by_name=True)

    ok: bool = True
