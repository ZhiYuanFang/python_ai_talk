## Context

Python 项目作为 go_ai_talk 的兄弟仓，需要通过 HTTP 调用 go_ai_talk 的 history-service 和 device-service 获取业务数据（事件字典、历史记录、宝宝画像）。当前 Python 侧 `http_client.py` 中的 4 个接口路径全部不匹配 Go 实际接口，导致服务完全无法通信。

### 当前 Python 调用的 4 个接口（全部错误）

| # | Python 路径 | 实际用途 |
|---|------------|---------|
| 1 | `GET /api/events/dictionary` | 获取事件字典（所有事件类型及别名） |
| 2 | `GET /api/events/list` | 获取设备历史记录（支持时间范围+limit） |
| 3 | `GET /device/history/api/filter` | 按条件筛选历史（多 eventIds + 时间范围） |
| 4 | `GET /api/device/{no}/baby` | 获取宝宝画像（生日、性别、名字） |

### Go 侧实际存在的对应接口

| # | Go 路径 | 服务 | 与 Python 的差异 |
|---|--------|------|----------------|
| 1 | `GET /device/history/api/event/options` | history-service | 路径不同，返回外层 `{"list":[...]}`，字段 camelCase |
| 2 | `GET /device/history/api/list` | history-service | 路径不同，参数仅支持 page/pageSize（不支持时间范围） |
| 3 | `GET /device/history/api/piece` | history-service | 仅支持单个 eventId，不支持多 eventIds |
| 4 | `GET /device/history/api/birthday` | history-service | 路径不同，参数 deviceNo 为 query 而非 path |

### Go 侧 Event 和 History 实体

```go
// Event 事件字典
type Event struct {
    Id         int64  // Python 需要映射为 event_id
    Name       string // Python 需要映射为 event_name
    EventType  string // number / time / one
    Unit       string // 计数单位
    ExtraNames string // 逗号分隔的别名
    Color      string
    Logo       string
    ParentId   int64  // Python 需要映射为 parent_id
}

// History 历史记录
type History struct {
    Id          int64
    DeviceNo    string
    EventId     int64
    EventName   string
    EventNumber int64
    EventUnit   string
    StartTime   int64  // Unix 秒
    EndTime     int64  // Unix 秒
    Remark      string
    PostId      uint64
    MediaType   int
    ImageKeys   string
    VideoKey    string
}
```

## Goals / Non-Goals

**Goals:**
- Python 侧所有 4 个接口能正确调用 Go 服务并拿到数据
- Go 侧新增历史筛选 filter 接口，支持多 eventIds + 时间范围 + limit
- Go 侧扩展 list 接口，支持 startTime、endTime、limit 可选参数
- Python 侧在 Go filter 接口未就绪时自动降级（全量拉取 + 本地过滤）

**Non-Goals:**
- 不改变 Python 侧业务逻辑（仅修复通信层）
- 不改变 Go 侧现有接口行为（所有新增参数可选，向后兼容）
- 不在 Python 侧持久化任何数据（保持 Go 为唯一数据源）

## Decisions

### 决策 1：Python 侧统一从 history-service 取所有数据

**选择**：4 个接口全部走 history-service（`/device/history/api/*`），不走 device-service

**理由**：
- 事件字典：两个服务都有，但 history-service 更贴近 Python 使用场景（历史查询 + 事件匹配）
- 历史记录、宝宝画像：只有 history-service 有
- 统一一个服务，减少 Python 的配置项和依赖复杂度

### 决策 2：Python 侧适配 camelCase 和 list 外层包装，而非 Go 新增专用接口

**选择**：Python 侧解析时做字段名转换（`id`→`event_id`、`name`→`event_name`、`parentId`→`parent_id`），并从 `response["list"]` 取数据

**理由**：
- Go 侧接口是标准对外接口，已经有其他调用方（前端、移动端）
- Python 侧改动量极小，每个方法只需加几行转换代码
- 避免 Go 侧维护 Python 专用接口，减少长期维护成本

### 决策 3：Go 侧新增 filter 接口而非扩展 piece 接口

**选择**：新增 `GET /device/history/api/filter`，支持多 eventIds

**理由**：
- `piece` 接口语义明确为"单事件区段查询"，已有调用方
- 新增独立接口语义清晰，不破坏现有 piece 接口的契约
- 向后兼容，零风险

### 决策 4：list 接口扩展参数全部可选，默认保持原有分页行为

**选择**：`/device/history/api/list` 新增 `startTime`、`endTime`、`limit` 三个可选 query 参数

**理由**：
- 不影响现有调用方（前端传 page/pageSize 行为不变）
- Python 侧可以传 limit 替代分页，更符合"取最近 N 条"的语义
- startTime/endTime 可以按时间窗口过滤，避免取全量

## Risks / Trade-offs

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Go 侧 filter 接口尚未部署，Python filter 调用失败 | 中 | Python 侧已有降级逻辑：filter 失败回退到全量 list + 本地过滤 |
| 字段名转换遗漏（camelCase → snake_case） | 低 | 全面测试，对照 Go entity 逐一核对 |
| list 接口扩展参数与现有分页参数冲突 | 低 | 优先级：limit > pageSize（传了 limit 就用 limit，否则用 pageSize） |
| Go 侧 filter 接口 SQL 性能（多 IN 查询） | 中 | device_no + start_time 建联合索引，event_id IN 列表限制长度（≤50） |

## Migration Plan

1. **第一步（Python 立即可做）**：修复 Python 侧 http_client.py 的 4 个接口路径和返回值解析，filter 接口先走降级逻辑
2. **第二步（Go 侧）**：在 history-service 新增 `/device/history/api/filter` 接口
3. **第三步（Go 侧）**：扩展 `/device/history/api/list` 增加 startTime/endTime/limit 可选参数
4. **第四步（Python 优化）**：Go filter 接口部署后，Python 自动命中 filter，无需降级
5. **回滚方案**：所有改动均为新增或可选，回滚只需恢复 Python 侧旧路径即可（Go 侧无需改动）
