"""
小贴士请求和响应数据模型

业务说明：
定义小贴士接口的请求和响应数据结构，与 Go 项目的调用格式保持一致。

设计思路：
1. 使用 Pydantic 定义数据模型，提供类型安全
2. Go↔Python 内部请求 JSON 以 snake_case 为权威（device_no）
3. camel 仅为过渡双收（deviceNo）；禁止要求 Go 改 camel
4. 月龄与当前时间由 Python 派生，请求体不再包含 baby_age_months / current_time
5. 流式响应模型复用 ClinicStreamResponse 的格式（type + content）
"""

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from app.feeding.schemas.intent import ClinicStreamResponse, ModelConfig


class TipRequest(BaseModel):
    """
    小贴士生成请求模型

    业务说明：
    封装小贴士生成接口的请求参数，由 Go voice 经 PythonAIClient 调用。
    仅含触发事件、设备编号与模型配置；月龄在 fetch_baby_profile 后自算，
    当前时间在写提示词时用 Asia/Shanghai 生成。

    设计思路：
    内部契约以 snake_case 为准；过渡期 AliasChoices 双收 camel，
    保证 Go TipStreamRequest snake body 可通过校验。
    """

    # 允许按字段名（snake）或 alias（camel）入站反序列化
    model_config = ConfigDict(populate_by_name=True)

    event_id: int = Field(..., description="触发事件ID")
    event_name: str = Field(..., description="触发事件名称")
    # 权威键 device_no；过渡双收 deviceNo（内联 Field，勿用共享 Annotated 别名）
    device_no: str = Field(
        ...,
        validation_alias=AliasChoices("device_no", "deviceNo"),
        description="设备编号（内部契约 snake_case，可过渡双收 camel）",
    )
    model: ModelConfig = Field(..., description="模型配置")


# 小贴士流式响应复用 ClinicStreamResponse
# 业务说明：SSE 事件格式与诊疗一致，{"type": "thinking|answer", "content": "..."}
TipStreamResponse = ClinicStreamResponse
