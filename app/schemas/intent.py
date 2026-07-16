"""
意图分析相关的数据模型

业务说明：
定义意图分析接口的请求和响应数据结构，确保与 Go 项目的格式兼容。

设计思路：
1. 使用 Pydantic 定义数据模型，提供类型安全
2. 请求模型与 Go 项目的调用格式保持一致
3. 响应模型与 Go 项目的 deepSeekUnifiedIntent 结构体保持一致
"""

from typing import List, Optional

from pydantic import BaseModel, Field


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
    封装意图分析接口的请求参数，与 Go 项目的调用格式保持一致。
    """
    text: str = Field(..., description="用户输入的自然语言文本")
    device_no: str = Field(..., alias="deviceNo", description="设备编号")
    model: ModelConfig = Field(..., description="模型配置")


class IntentResponse(BaseModel):
    """
    意图分析响应模型

    业务说明：
    封装意图分析接口的响应数据，与 Go 项目的 deepSeekUnifiedIntent 结构体保持一致。
    """
    target_type: str = Field(..., description="目标类型：feeding, history, suggest, conversation, exit")
    action: str = Field(..., description="动作类型：start, end, one, search, suggestion, reply, exit")
    event_name: str = Field("", description="事件名称（喂养场景）")
    keywords: List[str] = Field([], description="匹配的关键词列表")
    content: str = Field("", description="回答内容（对话场景）")


class ClinicRequest(BaseModel):
    """
    胖宝诊疗请求模型

    业务说明：
    封装胖宝诊疗接口的请求参数。
    """
    question: str = Field(..., description="用户的诊疗问题")
    device_no: str = Field(..., alias="deviceNo", description="设备编号")
    model: ModelConfig = Field(..., description="模型配置")


class ClinicStreamResponse(BaseModel):
    """
    胖宝诊疗流式响应模型

    业务说明：
    封装胖宝诊疗接口的流式响应数据，包含思考过程和回答内容。
    """
    type: str = Field(..., description="消息类型：thinking, answer")
    content: str = Field("", description="内容（思考或回答）")