## Context

Go 项目（`go_ai_talk`）的 `PythonAIClient.submitFeedback()` 方法通过 JSON Body 发送反馈数据到 Python 服务的两个接口：
- `POST /v1/clinic/feedback`
- `POST /v1/tip/feedback`

Go 侧发送的数据格式为：
```json
{"answer_id": "xxx", "feedback": 1}
```

但 Python 侧的两个函数签名使用 `(answer_id: str, feedback: int)`，FastAPI 默认将非 Pydantic 模型的参数视为 Query 参数，导致参数接收方式不匹配。

```
┌─────────────────────────────────────────────────────────┐
│                    当前不匹配的状态                        │
└─────────────────────────────────────────────────────────┘

  Go 侧 (发送)                    Python 侧 (接收)
  ───────────────                  ─────────────────
  POST /v1/clinic/feedback   →    async def clinic_feedback(
  Content-Type: application/json         answer_id: str,      ← Query!
  Body: {"answer_id":"...",             feedback: int         ← Query!
         "feedback": 1}               )

                                  ❌ 不匹配！期望 JSON Body
```

## Goals / Non-Goals

**Goals:**
- 将 Python 侧两个 feedback 接口的参数接收方式从 Query 改为 JSON Body，与 Go 侧发送方式对齐
- 在 `app/shared/schemas/` 下创建共享的 Pydantic 模型，供两个模块复用
- 将 feedback 值的校验（只能是 1 或 -1）前移到 Pydantic validator 层

**Non-Goals:**
- 不修改 Go 侧代码（Go 侧已经是正确的 JSON Body 方式）
- 不修改接口 URL
- 不修改响应格式
- 不修改业务逻辑（反馈频率限制、质量分更新等保持不变）
- 不修改任何流式接口

## Decisions

### 决策 1：Pydantic 模型放在 `app/shared/schemas/`

**决定**：在 `app/shared/schemas/` 下创建 `feedback.py`，定义 `FeedbackRequest` 模型。clinic 和 tip 两个模块都从这里 import。

**理由**：
- 两个 feedback 接口使用完全相同的请求格式（answer_id + feedback）
- Go 侧本身就是共用一个 `FeedbackRequest` 结构体
- 与项目中其他共享组件（llm_client、vector_store、http_client、共享图节点）的组织方式一致

**备选方案**：分别在各自模块的 schemas 中定义 → 放弃，会产生重复代码，且不符合 DRY 原则

### 决策 2：feedback 校验使用 Pydantic field_validator

**决定**：在 `FeedbackRequest` 模型中使用 `@field_validator('feedback')` 限制值只能是 1 或 -1，不再在函数体中做 `if feedback not in [1, -1]` 判断。

**理由**：
- 校验逻辑属于请求模型的职责，放在 Pydantic 层更符合 FastAPI 最佳实践
- 错误信息由 FastAPI 自动生成 422 响应，格式标准化
- 函数体逻辑更简洁，专注于业务处理

**备选方案**：保留函数体中的 if 判断 → 放弃，与 Pydantic validator 功能重复

### 决策 3：使用 Pydantic v2 field_validator（而非 v1 validator）

**决定**：使用 `pydantic.field_validator` 装饰器，与项目中现有 Pydantic v2 的用法保持一致。

**理由**：
- 项目使用的是 Pydantic v2（从 `model_dump()` 的使用可以看出）
- `field_validator` 是 v2 的推荐用法

## Risks / Trade-offs

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 其他非 Go 客户端（如 curl 或测试脚本）用 Query 参数调用 feedback 接口会失败 | 低，因为 feedback 接口的唯一调用方是 Go 服务 | 在 proposal 中明确标注这是一个轻微的破坏性变更，实际无影响 |
| Pydantic validator 返回的错误格式与原有 HTTPException 不同 | 低，422 有标准错误格式，且 feedback 接口无前端直连 | 确认 Go 侧不依赖具体的错误格式，只检查 HTTP 状态码 |
