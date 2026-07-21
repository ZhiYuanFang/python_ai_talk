## Why

当前系统仅支持单事件识别，一次只能处理一个喂养事件。用户输入如"没吃，睡着了"包含多个独立意图（结束喂养+开始睡眠），但系统只能识别其中一个事件，导致用户体验不佳。需要扩展意图分析和 Go 侧落库逻辑，支持一次识别并记录多个事件。

## What Changes

- **Python 侧**：扩展意图分析逻辑，支持返回多个事件意图结果
- **Python 侧**：修改意图分类提示词，引导 LLM 识别复合意图
- **Python 侧**：更新数据飞轮，支持多事件的用户表达记录
- **Go 侧**：修改 `handleUnifiedIntentAction`，支持一次处理多个事件并落库
- **Go 侧**：扩展 `deepSeekUnifiedIntent` 结构，支持多事件列表
- **API 接口**：更新 `IntentResponse` 结构，支持返回多事件列表

## Capabilities

### New Capabilities

- `multi-event-recognition`: 支持用户输入中包含多个喂养事件的识别和处理
- `intent-response-multi-event`: 更新意图分析响应结构，支持返回多事件列表

### Modified Capabilities

- `feeding-intent-user-confirmation`: 确认流程需要支持多事件的批量确认
- `intent-analysis`: 意图分析核心逻辑扩展支持多事件

## Impact

- **Python 侧**：
  - `app/feeding/graphs/nodes/classify_intent.py`: 修改意图分类逻辑
  - `app/feeding/graphs/nodes/prompts/intent_classification.py`: 更新提示词
  - `app/feeding/graphs/nodes/handle_feedback.py`: 修改数据飞轮逻辑
  - `app/feeding/schemas/intent.py`: 更新响应结构
  - `app/api/routes/intent.py`: 更新响应构建逻辑

- **Go 侧**：
  - `internal/services/voice/voice_chat_understanding.go`: 修改意图处理逻辑
  - `internal/services/voice/python_ai_client.go`: 更新响应结构

- **API 接口**：
  - `/v1/analyze/intent`: 响应结构增加 events 字段
  - `/v1/analyze/intent/confirm`: 支持多事件确认反馈