## Capability: multi-event-recognition

### Description

支持用户输入中包含多个喂养事件的识别和处理，如"没吃，睡着了"可同时识别为"结束喂养"和"开始睡眠"两个独立事件。

### Requirements

#### R1: 多事件识别

**Description:** 系统应能识别用户输入中的多个喂养事件

**Acceptance Criteria:**
- 当用户输入包含多个喂养事件时（如"没吃，睡着了"），LLM 应返回包含多个事件的列表
- 每个事件应包含 action、event_name、event_id 字段
- 最多支持识别 3 个事件，超过时只取前 3 个

#### R2: 确认流程

**Description:** 多事件场景下，确认流程应支持批量确认

**Acceptance Criteria:**
- `prepare_confirm` 节点应生成包含所有事件的确认消息
- 用户确认后，所有事件一起落库
- 用户取消后，所有事件都不落库

#### R3: 数据飞轮

**Description:** 用户确认后，完整用户表达应添加到向量库

**Acceptance Criteria:**
- 用户确认多事件后，将完整用户表达关联到第一个事件添加到向量库
- 后续相同输入应能直接向量匹配成功
- 匹配成功时返回所有关联事件

#### R4: 向后兼容

**Description:** 单事件场景应保持原有行为

**Acceptance Criteria:**
- 单事件输入（如"开始母乳"）应使用原有字段返回结果
- Go 侧应优先检查 events 字段，为空时使用原有字段
- 现有 API 调用方无需修改即可正常工作

### API Changes

#### IntentResponse 结构扩展

**新增字段:**
- `events`: 多事件列表，每个元素包含 action、event_name、event_id

**示例响应：**
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
    "keywords": [],
    "content": "",
    "need_confirm": false,
    "confirm_message": "",
    "conversation_id": ""
}
```

#### Go 侧 deepSeekUnifiedIntent 结构扩展

**新增字段:**
- `Events`: 多事件列表

**示例结构：**
```go
type deepSeekUnifiedIntent struct {
    Action        string `json:"action"`
    EventName     string `json:"event_name"`
    EventId       string `json:"event_id"`
    Events        []IntentEvent `json:"events"`
    // ... 其他字段
}

type IntentEvent struct {
    Action     string `json:"action"`
    EventName  string `json:"event_name"`
    EventId    string `json:"event_id"`
}
```

### Dependencies

- `intent-analysis`: 意图分析核心逻辑
- `feeding-intent-user-confirmation`: 确认流程