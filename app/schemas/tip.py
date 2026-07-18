"""
小贴士请求和响应数据模型

业务说明：
定义小贴士接口的请求和响应数据结构，与 Go 项目的调用格式保持一致。

设计思路：
1. 使用 Pydantic 定义数据模型，提供类型安全
2. 请求模型包含事件信息、设备编号、月龄、时间、模型配置
3. 流式响应模型复用 ClinicStreamResponse 的格式（type + content）
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.intent import ModelConfig, ClinicStreamResponse


class TipRequest(BaseModel):
    """
    小贴士生成请求模型

    业务说明：
    封装小贴士生成接口的请求参数，由 Go history service 调用。
    包含触发事件信息、设备编号、宝宝月龄、当前时间和模型配置。
    """

    event_id: int = Field(..., description="触发事件ID")
    event_name: str = Field(..., description="触发事件名称")
    device_no: str = Field(..., alias="deviceNo", description="设备编号")
    baby_age_months: int = Field(..., alias="babyAgeMonths", description="宝宝月龄")
    current_time: int = Field(..., alias="currentTime", description="当前触发时间（unix 秒）")
    model: ModelConfig = Field(..., description="模型配置")


# 小贴士流式响应复用 ClinicStreamResponse
# 业务说明：SSE 事件格式与诊疗一致，{"type": "thinking|answer", "content": "..."}
TipStreamResponse = ClinicStreamResponse
