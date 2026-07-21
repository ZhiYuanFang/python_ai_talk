## 1. Python 侧 - 意图分类提示词扩展

- [x] 1.1 修改 `app/feeding/graphs/nodes/prompts/intent_classification.py`，增加多事件识别的意图类型说明
- [x] 1.2 在提示词中增加多事件的 JSON 返回格式示例

## 2. Python 侧 - 意图分类逻辑扩展

- [x] 2.1 修改 `app/feeding/graphs/nodes/classify_intent.py` 的 `_parse_intent_result` 函数，支持解析多事件列表
- [x] 2.2 在 `classify_intent` 函数中增加多事件的提取和处理逻辑
- [x] 2.3 限制最多返回 3 个事件，超过时只取前 3 个

## 3. Python 侧 - IntentResult 结构扩展

- [x] 3.1 在 `app/feeding/graphs/nodes/classify_intent.py` 的默认结果中增加 `events` 字段
- [x] 3.2 修改 `_match_feeding_event` 函数，支持多事件的事件名匹配

## 4. Python 侧 - 确认流程扩展

- [x] 4.1 修改 `app/feeding/graphs/nodes/prepare_confirm.py`，支持生成多事件的确认消息
- [x] 4.2 当事件超过 2 个时，使用简化的确认消息格式

## 5. Python 侧 - 数据飞轮扩展

- [x] 5.1 修改 `app/feeding/graphs/nodes/handle_feedback.py`，支持多事件场景下的数据飞轮
- [x] 5.2 用户确认后，将完整用户表达关联到第一个事件添加到向量库

## 6. Python 侧 - IntentResponse 结构扩展

- [x] 6.1 修改 `app/feeding/schemas/intent.py`，在 `IntentResponse` 中增加 `events` 字段
- [x] 6.2 增加 `IntentEvent` 模型用于描述单个事件

## 7. Python 侧 - API 路由扩展

- [x] 7.1 修改 `app/api/routes/intent.py` 的 `analyze_intent` 函数，支持构建多事件响应
- [x] 7.2 修改 `app/api/routes/intent.py` 的 `_stream_intent_response` 函数，支持流式返回多事件
- [x] 7.3 修改 `app/api/routes/intent.py` 的 `confirm_intent` 函数，支持多事件确认

## 8. Go 侧 - deepSeekUnifiedIntent 结构扩展

- [x] 8.1 修改 `internal/services/voice/python_ai_client.go`，增加 `IntentEvent` 结构体
- [x] 8.2 在 `deepSeekUnifiedIntent` 中增加 `Events` 字段

## 9. Go 侧 - PythonAIClient 响应结构扩展

- [x] 9.1 修改 `internal/services/voice/python_ai_client.go`，增加 `IntentEvent` 结构体
- [x] 9.2 在 `AnalyzeIntentResponse` 中增加 `Events` 字段

## 10. Go 侧 - 意图处理逻辑扩展

- [x] 10.1 修改 `internal/services/voice/voice_chat_understanding.go` 的 `handleUnifiedIntentAction` 函数，支持多事件批量落库
- [x] 10.2 在 `callDeepSeekUnifiedIntent` 函数中增加多事件的映射逻辑

## 11. 验证与测试

- [x] 11.1 验证单事件场景仍正常工作（向后兼容）
- [x] 11.2 验证多事件场景能正确识别和处理（如"没吃，睡着了"）
- [x] 11.3 验证确认流程支持多事件批量确认
- [x] 11.4 验证数据飞轮支持多事件的用户表达记录
- [x] 11.5 验证 Go 项目编译通过