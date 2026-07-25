## ADDED Requirements

### Requirement: Python HTTP 客户端接口路径对齐 Go 服务

Python 服务的 `HttpClient` 类 SHALL 将所有兄弟仓 API 调用路径对齐到 go_ai_talk 服务实际存在的接口路径。

#### Scenario: 调用事件字典接口
- **WHEN** Python 调用 `get_event_dictionary()`
- **THEN** 请求路径 SHALL 为 `GET /device/history/api/event/options`
- **AND** 响应解析 SHALL 从 `data["list"]` 提取事件列表
- **AND** 每个事件字段 SHALL 做 camelCase → snake_case 转换（`id`→`event_id`、`name`→`event_name`、`parentId`→`parent_id`）

#### Scenario: 调用全量历史接口
- **WHEN** Python 调用 `get_history_events(device_no, start_time, end_time, limit)`
- **THEN** 请求路径 SHALL 为 `GET /device/history/api/list`
- **AND** 参数 SHALL 以 query 方式传递（`deviceNo`、`startTime`、`endTime`、`limit`）
- **AND** 响应解析 SHALL 从 `data["list"]` 提取历史列表

#### Scenario: 调用筛选历史接口（Go filter 接口就绪时）
- **WHEN** Python 调用 `get_filtered_history_events(device_no, event_ids, start_time, end_time, limit)` 且 Go filter 接口可用
- **THEN** 请求路径 SHALL 为 `GET /device/history/api/filter`
- **AND** `event_ids` SHALL 以逗号分隔字符串作为 query 参数 `eventIds` 传递
- **AND** 响应解析 SHALL 从 `data["list"]` 提取历史列表

#### Scenario: 调用筛选历史接口（Go filter 接口未就绪时降级）
- **WHEN** Python 调用 `get_filtered_history_events()` 且 filter 接口返回 404 或错误
- **THEN** Python SHALL 自动降级为调用 `get_history_events()` 拉取全量数据
- **AND** 在本地按 `event_ids` 和时间范围过滤数据后返回

#### Scenario: 调用宝宝画像接口
- **WHEN** Python 调用 `get_baby_profile(device_no)`
- **THEN** 请求路径 SHALL 为 `GET /device/history/api/birthday`
- **AND** `device_no` SHALL 以 query 参数 `deviceNo` 传递（非 path）
- **AND** 404 时 SHALL 返回 `None`，其他错误 SHALL 抛出异常

### Requirement: Go 侧新增历史筛选接口

Go 的 history-service SHALL 提供 `GET /device/history/api/filter` 接口，支持按多事件ID和时间范围筛选历史记录。

#### Scenario: 按多事件ID和时间范围筛选
- **WHEN** 收到请求 `GET /device/history/api/filter?deviceNo=d1&eventIds=1,2,3&startTime=1000&endTime=2000&limit=50`
- **THEN** 返回该设备在时间范围内、事件ID为 1/2/3 的历史记录
- **AND** 返回结果 SHALL 按 `startTime` 倒序排列
- **AND** 返回条数 SHALL 不超过 `limit`（默认 100）

#### Scenario: 不传 eventIds 时返回所有事件类型
- **WHEN** 请求中 `eventIds` 为空或未提供
- **THEN**  SHALL 不限制事件类型，返回该设备时间范围内所有历史记录

#### Scenario: 不传时间参数时不限制时间
- **WHEN** 请求中 `startTime` 或 `endTime` 未提供
- **THEN**  SHALL 跳过对应时间条件，不限制时间范围

### Requirement: Go 侧扩展全量历史接口支持时间范围

Go 的 `GET /device/history/api/list` 接口 SHALL 扩展支持 `startTime`、`endTime`、`limit` 可选 query 参数。

#### Scenario: 传时间范围时按时间过滤
- **WHEN** 请求同时带有 `startTime` 和 `endTime`
- **THEN** 返回结果 SHALL 限制在该时间范围内

#### Scenario: 传 limit 时限制返回条数
- **WHEN** 请求带有 `limit` 参数
- **THEN** 返回条数 SHALL 不超过 `limit`（优先级高于 pageSize）

#### Scenario: 不传新参数时保持原有分页行为
- **WHEN** 请求仅带 `page` 和 `pageSize`（原有调用方式）
- **THEN** 行为 SHALL 与扩展前完全一致（向后兼容）
