"""
反馈接口请求模型

业务说明：
定义诊疗和小贴士两个反馈接口共享的请求数据模型，与 Go 侧的 FeedbackRequest
结构体保持一致。Go 侧通过 JSON Body 发送 {"answer_id": "xxx", "feedback": 1}，
本模型用于接收并校验该请求。

设计思路：
1. 使用 Pydantic v2 定义模型，与项目其他 schemas 的用法保持一致
2. answer_id 字段对应流式响应 done 事件中返回的回答 ID
3. feedback 字段使用 field_validator 限制只能为 1（👍）或 -1（👎）
4. 该模型由 clinic 和 tip 两个模块共享使用
"""

from pydantic import BaseModel, Field, field_validator


class FeedbackRequest(BaseModel):
    """
    反馈请求模型

    业务说明：
    封装用户反馈接口的请求参数，与 Go 侧 submitFeedback() 的发送格式保持一致。
    被 /v1/clinic/feedback 和 /v1/tip/feedback 两个接口共用。

    字段说明：
    - answer_id: 回答 ID，由流式响应的 done 事件返回，格式为 clinic_{uuid} 或 tip_{uuid}
    - feedback: 反馈值，1=👍（有帮助），-1=👎（无帮助）
    """

    answer_id: str = Field(
        ...,
        description="回答 ID（由流式响应的 done 事件返回，格式：clinic_{uuid} 或 tip_{uuid}）",
    )

    feedback: int = Field(
        ...,
        description="反馈值：1=👍（有帮助），-1=👎（无帮助）",
    )

    @field_validator("feedback")
    @classmethod
    def validate_feedback(cls, v: int) -> int:
        """
        校验 feedback 字段值

        业务逻辑：
        feedback 只能为 1（👍有帮助）或 -1（👎无帮助），其他值均视为非法输入。
        该校验在请求解析阶段执行，不合法的值会被 FastAPI 自动返回 422 错误。

        Args:
            v: 传入的 feedback 值

        Returns:
            校验通过的 feedback 值

        Raises:
            ValueError: feedback 值不在允许范围内
        """
        if v not in (1, -1):
            raise ValueError("feedback 值必须为 1（👍）或 -1（👎）")
        return v
