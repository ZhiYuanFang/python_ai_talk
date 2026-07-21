## Capability: intent-response-multi-event

### Description

更新意图分析响应结构，支持返回多事件列表，保持向后兼容性。

### Requirements

#### R1: IntentResponse 结构扩展

**Description:** 在 IntentResponse 中增加 events 字段支持多事件

**Acceptance Criteria:**
- `events` 字段为列表类型，每个元素包含 action、event_name、event_id
- 单事件场景下 events 为空列表
- 多事件场景下 action 为 "multi"，events 包含所有事件

#### R2: 响应构建逻辑

**Description:** 路由层应根据意图结果构建正确的响应

**Acceptance Criteria:**
- 单事件场景：使用原有字段（event_name、action、event_id）
- 多事件场景：使用 events 列表，action 设为 "multi"
- 需要确认时，确认消息应包含所有事件

#### R3: 流式响应支持

**Description:** 流式接口应支持多事件响应

**Acceptance Criteria:**
- `/v1/analyze/intent/stream` 应返回包含 events 的响应
- 流式 answer 事件应包含完整的多事件信息

### API Changes

#### IntentResponse 结构

**新增字段:**
```python
class IntentResponse(BaseModel):
    target_type: str
    action: str
    event_name: str = ""
    event_id: str = ""
    events: List[Dict[str, str]] = []  # 新增：多事件列表
    keywords: List[str] = []
    content: str = ""
    need_confirm: bool = False
    confirm_message: str = ""
    conversation_id: str = ""
```

#### 响应示例

**单事件响应：**
```json
{
    "target_type": "feeding",
    "action": "start",
    "event_name": "母乳喂养",
    "event_id": "1",
    "events": [],
    "keywords": ["开始", "母乳"],
    "content": "",
    "need_confirm": false,
    "confirm_message": "",
    "conversation_id": ""
}
```

**多事件响应：**
```json
{
    "target_type": "feeding",
    "action": "multi",
    "event_name": "",
    "event_id": "",
    "events": [
        {"action": "end", "event_name": "母乳喂养", "event_id": "1"},
        {"action": "start", "event_name": "睡眠", "event_id": "2"}
    ],
    "keywords": ["没吃", "睡着了"],
    "content": "",
    "need_confirm": true,
    "confirm_message": "您是要：结束记录「母乳喂养」，开始记录「睡眠」吗？请回复「确认」或「取消」。",
    "conversation_id": "abc-123"
}
```

### Dependencies

- `multi-event-recognition`: 多事件识别能力