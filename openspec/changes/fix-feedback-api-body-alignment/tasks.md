## 1. 创建共享 schemas 目录和 FeedbackRequest 模型

- [x] 1.1 创建 `app/shared/schemas/` 目录
- [x] 1.2 创建 `app/shared/schemas/__init__.py`
- [x] 1.3 创建 `app/shared/schemas/feedback.py`，定义 `FeedbackRequest` Pydantic 模型
- [x] 1.4 `FeedbackRequest` 包含 `answer_id: str` 和 `feedback: int` 两个字段
- [x] 1.5 使用 `@field_validator('feedback')` 限制 feedback 只能是 1 或 -1

## 2. 修改 clinic feedback 接口

- [x] 2.1 在 `app/api/routes/clinic.py` 中导入 `FeedbackRequest`
- [x] 2.2 将 `clinic_feedback()` 函数签名改为 `async def clinic_feedback(request: FeedbackRequest)`
- [x] 2.3 删除函数体中的 `if feedback not in [1, -1]` 校验（已由 Pydantic validator 承担）
- [x] 2.4 将函数体中所有 `answer_id` 引用改为 `request.answer_id`
- [x] 2.5 将函数体中所有 `feedback` 引用改为 `request.feedback`
- [x] 2.6 更新 docstring 中的 Args 部分

## 3. 修改 tip feedback 接口

- [x] 3.1 在 `app/api/routes/tip.py` 中导入 `FeedbackRequest`
- [x] 3.2 将 `tip_feedback()` 函数签名改为 `async def tip_feedback(request: FeedbackRequest)`
- [x] 3.3 删除函数体中的 `if feedback not in [1, -1]` 校验
- [x] 3.4 将函数体中所有 `answer_id` 引用改为 `request.answer_id`
- [x] 3.5 将函数体中所有 `feedback` 引用改为 `request.feedback`
- [x] 3.6 更新 docstring 中的 Args 部分

## 4. 验证测试

- [x] 4.1 Python 侧所有修改文件语法检查通过（`python -m py_compile`）
- [x] 4.2 全局搜索确认没有遗漏的旧参数引用
- [x] 4.3 验证服务可正常启动（无 ImportError）
- [x] 4.4 使用 curl 测试 `/v1/clinic/feedback` 接口接收 JSON Body 正常
- [x] 4.5 使用 curl 测试 `/v1/tip/feedback` 接口接收 JSON Body 正常
- [x] 4.6 测试 feedback 非法值（非 1/-1）返回 422
