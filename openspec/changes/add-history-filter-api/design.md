## Context

当前 python_ai_talk 的意图分析接口存在三个关键问题：

1. **缺少意图后处理**: `analyze_intent` 只做意图分类，当识别到 `history` 或 `suggest` 意图时，没有拉取历史数据和向量库知识来生成回答
2. **历史数据筛选能力不足**: go_ai_talk 的 history-service 现有 API `/device/history/api/list` 只支持分页，不支持按事件类型筛选；`/device/history/api/piece` 只支持单个事件类型
3. **无法动态判断数据需求**: Python 侧无法根据用户自然语言问题判断需要拉取什么类型、什么时间范围的历史数据

本设计针对这三个问题，提出完整的解决方案：
- Go 侧新增支持多事件类型筛选的 API
- Python 侧增加意图后处理阶段，使用 LLM 动态判断数据需求

## Goals / Non-Goals

**Goals:**

1. Go 侧新增 `/device/history/api/filter` API，支持多事件ID（逗号分隔）和时间范围筛选
2. Python 侧 `analyze_intent` 增加意图后处理：
   - `history` 意图：动态判断事件ID和时间范围 → 拉取历史 → LLM 生成回答
   - `suggest` 意图：动态判断事件ID和时间范围 → 拉取历史 + 向量检索 + 宝宝画像 → LLM 生成建议
3. Python 侧 `clinic_stream` 增加动态判断历史数据范围的能力
4. 保持与 go_ai_talk 的兼容性，返回相同的 JSON 结构
5. 所有新增代码添加中文业务逻辑注释

**Non-Goals:**

1. 不修改 `feeding` 和 `conversation` 意图的处理逻辑
2. 不修改 go_ai_talk 现有 `/device/history/api/list` 和 `/device/history/api/piece` API
3. 不涉及 CI/CD 流程调整

## Decisions

### D1: Go 侧新增独立 Filter API（而非扩展现有 List API）

**决定**: 在 `HistoryCtrl` 中新增 `Filter` 方法，对应路径 `/device/history/api/filter`，而非扩展现有 `List` 方法。

**理由**:
- 避免破坏现有 API 契约（`List` 接口被其他客户端使用）
- `Filter` API 的返回格式与 `List` 不同（不需要分页，直接返回列表）
- 职责清晰：`List` 用于前端分页展示，`Filter` 用于 Python 侧批量筛选

**API 设计**:

```
GET /device/history/api/filter
参数:
  deviceNo: string (必填) - 设备编号
  eventIds: string (可选) - 事件ID列表，逗号分隔，如 "1,2"（事件ID不变而名称会变）
  startTime: int64 (可选) - 开始时间戳（毫秒）
  endTime: int64 (可选) - 结束时间戳（毫秒）
  limit: int (可选，默认 100) - 返回数量限制

返回:
{
  "list": [
    {
      "id": 1,
      "deviceNo": "xxx",
      "eventId": 1,
      "eventName": "奶粉喂养",
      "eventNumber": 120,
      "eventUnit": "ml",
      "startTime": 1234567890000,
      "endTime": 1234567900000,
      "remark": ""
    }
  ]
}
```

### D2: Python 侧两阶段 LLM 调用设计

**决定**: `analyze_intent` 采用两阶段 LLM 调用模式：

```
阶段 1: 意图分类（已有）
  输入: 用户问题 + 事件字典
  输出: { target_type, action, event_name, keywords, content }

阶段 2: 意图后处理（新增）
  根据 target_type 决定后续动作：
  - feeding → 直接返回（Go 侧处理 CRUD）
  - history → 调用 LLM 判断数据需求 → 拉取历史 → LLM 生成回答
  - suggest → 调用 LLM 判断数据需求 → 拉取历史 + 向量检索 + 宝宝画像 → LLM 生成建议
  - conversation → 兜底文案
  - exit → 直接返回
```

**理由**:
- 将意图分类和数据需求判断分离，降低单个 LLM 调用的复杂度
- 两阶段调用可以更好地控制 token 消耗
- 支持灵活的后处理逻辑，便于后续扩展

### D3: 使用 LLM 动态判断历史数据需求

**决定**: 在意图后处理阶段，使用独立的 LLM 调用判断需要拉取的历史数据：

**输入提示词**:
```
用户问题："今天喝了多少奶粉"
可用事件：[{"id": 1, "name": "奶粉喂养"}, {"id": 2, "name": "母乳喂养"}, {"id": 3, "name": "辅食"}, {"id": 4, "name": "睡觉"}, {"id": 5, "name": "排便"}, {"id": 6, "name": "吃药"}]

请分析用户问题，判断需要查询哪些类型的历史记录以及时间范围：

输出格式：
{
  "event_ids": [1],
  "time_range": "today",
  "limit": 20
}

time_range 可选值：
- "today": 今天（00:00 ~ 现在）
- "yesterday": 昨天
- "last_7_days": 最近7天
- "last_30_days": 最近30天
- "custom": 自定义时间范围（需同时提供 start_time 和 end_time）
```

**理由**:
- LLM 擅长理解自然语言中的时间和事件类型语义
- 避免硬编码规则，提高灵活性
- 用户问题千变万化，无法用简单规则覆盖所有场景

### D4: Python 侧新增 get_filtered_history_events HTTP 方法

**决定**: 在 `HttpClient` 中新增 `get_filtered_history_events` 方法，调用 go 侧新 API：

```python
async def get_filtered_history_events(
    self,
    device_no: str,
    event_ids: Optional[List[int]] = None,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """调用 history-service 的 filter API"""
```

**理由**:
- 封装 go 侧 API 调用，与现有 `get_history_events` 方法保持一致的风格
- 便于后续扩展和维护

## Risks / Trade-offs

### R1: 两阶段 LLM 调用增加延迟

**风险**: 意图分析从单次 LLM 调用变为两次，增加了响应延迟。

**缓解措施**:
- 阶段 1 和阶段 2 的 LLM 调用可以并行准备（如阶段 1 返回后立即发起阶段 2 的数据需求判断）
- 设置合理的超时时间，避免用户等待过长
- 对于简单意图（如 feeding、conversation），直接跳过阶段 2

### R2: LLM 判断数据需求可能出错

**风险**: LLM 可能误解用户意图，返回错误的事件类型或时间范围。

**缓解措施**:
- 设置 fallback 策略：如果 LLM 返回的事件ID不在事件字典中，使用空列表（拉取所有类型）
- 设置默认时间范围：如果 LLM 返回异常的 time_range，使用 "last_7_days"
- 记录 LLM 判断日志，便于监控和优化

### R3: Go 侧新 API 的性能问题

**风险**: 如果用户请求大量事件类型和大范围时间，查询可能较慢。

**缓解措施**:
- 设置 `limit` 参数的上限（如 100），避免返回过多数据
- 在数据库层面添加索引优化查询性能
- Python 侧对返回数据进行缓存，避免重复查询

### R4: 与 go_ai_talk 部署的兼容性

**风险**: Python 服务依赖新 API，如果 go 服务未升级到包含新 API 的版本，会导致请求失败。

**缓解措施**:
- 在 Python 侧添加版本检测或降级逻辑：如果新 API 不可用，回退到 `get_history_events` 拉取全量数据后在 Python 侧过滤
- 在部署文档中明确说明 Python 服务与 go 服务的版本依赖关系

## Migration Plan

### 阶段 1: Go 侧开发

1. 新增 API 请求/响应模型定义（`internal/model/api/v1/`）
2. 在 `HistoryCtrl` 中新增 `Filter` 方法
3. 在服务层实现过滤查询逻辑
4. 测试新 API

### 阶段 2: Python 侧开发

1. 在 `HttpClient` 中新增 `get_filtered_history_events` 方法
2. 在 `analyze_intent` 中增加意图后处理阶段
3. 新增 LLM 提示词构建函数（判断数据需求）
4. 测试完整流程

### 阶段 3: 联调测试

1. 部署 go_ai_talk 和 python_ai_talk
2. 测试历史查询和成长建议场景
3. 验证动态判断逻辑的正确性

### 回滚策略

如果新 API 或意图后处理逻辑出现问题：
1. Python 侧：关闭意图后处理开关，恢复为只做意图分类
2. Go 侧：新 API 不影响现有 API，无需回滚
