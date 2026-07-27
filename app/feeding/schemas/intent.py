"""
意图分析相关的数据模型

业务说明：
定义意图分析接口的请求和响应数据结构，确保与 Go 项目的格式兼容。

设计思路：
1. 使用 Pydantic 定义数据模型，提供类型安全
2. Go↔Python 内部请求 JSON 以 snake_case 为权威（如 device_no）；camel 仅为过渡双收
3. 响应模型与 Go 项目的 deepSeekUnifiedIntent 结构体保持一致
4. 支持流式响应（SSE）和用户确认机制
"""

from typing import Annotated, Any, Dict, List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ModelConfig(BaseModel):
    """
    模型配置

    业务说明：
    用于封装调用 LLM 时的模型配置参数，由 Go 服务传入。
    """
    provider: str = Field(..., description="LLM 提供商，可选值: deepseek, glm")
    name: str = Field(..., description="模型名称")
    max_in_flight: int = Field(3, description="最大并发数")


class IntentRequest(BaseModel):
    """
    意图分析请求模型

    业务说明：
    封装意图分析接口的请求参数，与 Go PythonAIClient 的调用格式保持一致。
    支持流式和非流式两种模式。
    同一输入框续聊时可携带 conversation_id，用于消歧/澄清 pending。

    设计思路：
    Go↔Python 内部契约以 snake_case 为准（device_no）；
    过渡期通过 AliasChoices 双收 camel（deviceNo），避免旧调用方瞬时断裂。
    禁止要求 Go 客户端改为 camel。
    """
    # 允许按字段名（snake）或 alias（camel）入站反序列化
    model_config = ConfigDict(populate_by_name=True)

    text: str = Field(..., description="用户输入的自然语言文本")
    # 权威键 device_no；过渡双收 deviceNo（字段级 Annotated，勿用模块级共享别名）
    device_no: Annotated[
        str,
        Field(
            validation_alias=AliasChoices("device_no", "deviceNo"),
            description="设备编号（内部契约 snake_case，可过渡双收 camel）",
        ),
    ]
    model: ModelConfig = Field(..., description="模型配置")
    # 流式返回开关，默认 false（非流式），true 时通过 SSE 返回 thinking 事件
    stream: Optional[bool] = Field(default=False, description="是否流式返回，默认false")
    # 可选会话 ID：存在 pending 消歧/澄清时带回，用于同一输入框续聊
    conversation_id: Optional[str] = Field(
        default=None,
        description="会话ID；有 pending 澄清时带回以续聊",
    )

class IntentEvent(BaseModel):
    """
    单个事件模型

    业务说明：
    用于描述喂养事件的单个条目，支持多事件场景的事件列表。
    """
    action: str = Field("", description="动作类型：start, end, one")
    event_name: str = Field("", description="事件名称")
    event_id: str = Field("", description="事件ID")
    quantity: Optional[int] = Field(default=None, description="从用户输入中提取的数量值")


class IntentResponse(BaseModel):
    """
    意图分析响应模型

    业务说明：
    封装意图分析接口的响应数据，与 Go 项目的 deepSeekUnifiedIntent 结构体保持一致。
    包含向量匹配、用户确认、数据飞轮和多事件相关字段。
    """
    target_type: str = Field(..., description="目标类型：feeding, history, suggest, conversation, exit")
    action: str = Field(..., description="动作类型：start, end, one, search, suggestion, reply, exit, multi")
    event_name: str = Field("", description="事件名称（喂养场景，单事件时使用）")
    event_id: str = Field("", description="事件ID（喂养场景，单事件时使用）")
    quantity: Optional[int] = Field(default=None, description="从用户输入中提取的数量值（Python 前置提取）")
    event_type: Optional[str] = Field(default=None, description="事件类型：number, time, one（新事件时 Python 返回）")
    event_unit: Optional[str] = Field(default=None, description="事件单位：ml、次、分钟（新事件时 Python 返回）")
    is_new_event: Optional[bool] = Field(default=False, description="是否为新事件")
    keywords: List[str] = Field([], description="匹配的关键词列表")
    content: str = Field("", description="回答内容（对话场景）")

    # 多事件列表（当action为multi时使用）
    events: List[IntentEvent] = Field([], description="多事件列表，当action为multi时返回")

    # 向量匹配置信度（0-1之间，值越大越相似）
    match_confidence: Optional[float] = Field(default=None, description="向量匹配置信度（0-1之间）")
    # 匹配来源（vector表示向量匹配，llm表示LLM分类）
    match_source: Optional[str] = Field(default=None, description="匹配来源：vector（向量匹配）或 llm（LLM分类）")
    # 是否需要用户澄清/确认（父事件消歧或叶子软确认）
    need_confirm: Optional[bool] = Field(
        default=False,
        description="是否需要用户澄清（同一输入框续聊）",
    )
    # 澄清类型：parent_disambiguation | leaf_confirm
    confirm_type: Optional[str] = Field(
        default=None,
        description="澄清类型：parent_disambiguation 或 leaf_confirm",
    )
    # 确认/澄清话术（need_confirm 为 True 时返回）
    confirm_message: Optional[str] = Field(
        default=None,
        description="澄清话术，当 need_confirm 为 True 时返回",
    )
    # 会话ID（用于同一 /intent 输入框续聊）
    conversation_id: Optional[str] = Field(
        default=None,
        description="会话ID，有 pending 澄清时返回，下一轮请求带回",
    )
    # 消歧选项（父事件子类列表等）
    options: List[IntentEvent] = Field(
        default_factory=list,
        description="澄清选项列表（如父事件下的子事件）",
    )


class IntentStreamResponse(BaseModel):
    """
    意图分析流式响应模型

    业务说明：
    封装意图分析流式接口的 SSE 事件数据。
    包含思考过程（thinking）和最终结果（answer）两种事件类型。
    """
    # 事件类型：thinking（节点思考进度）、answer（最终意图结果）
    type: str = Field(..., description="消息类型：thinking, answer")
    # 事件内容（thinking 时为思考文案，answer 时为意图结果JSON）
    content: str = Field("", description="内容（思考文案或回答内容）")
    # 节点名称（仅 thinking 事件，标识当前执行的节点）
    node: Optional[str] = Field(default=None, description="节点名称（thinking事件专用）")


class ClinicRequest(BaseModel):
    """
    胖宝诊疗请求模型

    业务说明：
    封装胖宝诊疗接口的请求参数，与 Go PythonAIClient 调用格式保持一致。

    设计思路：
    Go↔Python 内部契约以 snake_case 为准（device_no）；
    过渡期通过 AliasChoices 双收 camel（deviceNo）。
    禁止要求 Go 客户端改为 camel。
    """
    # 允许按字段名（snake）或 alias（camel）入站反序列化
    model_config = ConfigDict(populate_by_name=True)

    question: str = Field(..., description="用户的诊疗问题")
    # 权威键 device_no；过渡双收 deviceNo（字段级 Annotated，勿用模块级共享别名）
    device_no: Annotated[
        str,
        Field(
            validation_alias=AliasChoices("device_no", "deviceNo"),
            description="设备编号（内部契约 snake_case，可过渡双收 camel）",
        ),
    ]
    model: ModelConfig = Field(..., description="模型配置")


class ClinicStreamResponse(BaseModel):
    """
    胖宝诊疗流式响应模型

    业务说明：
    封装胖宝诊疗接口的流式响应数据，包含思考过程、回答内容和回答 ID（用于反馈）。
    """
    type: str = Field(..., description="消息类型：thinking, answer, done")
    content: str = Field("", description="内容（思考或回答）")
    answer_id: Optional[str] = Field(None, description="回答 ID（仅在 done 事件中返回，用于反馈）")
