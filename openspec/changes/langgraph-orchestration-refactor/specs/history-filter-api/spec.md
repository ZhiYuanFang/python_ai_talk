## ADDED Requirements

### Requirement: Go 侧新增历史记录筛选 API
go_ai_talk 的 history-service SHALL 新增 `/device/history/api/filter` 接口，支持按事件ID列表和时间范围筛选历史记录。

#### Scenario: 按事件ID筛选
- **WHEN** 请求 GET /device/history/api/filter?deviceNo=xxx&eventIds=1,2
- **THEN** 接口 SHALL 返回设备 xxx 的所有 eventId 为 1 和 2 的记录
- **AND** 忽略其他类型的记录

#### Scenario: 按时间范围筛选
- **WHEN** 请求 GET /device/history/api/filter?deviceNo=xxx&startTime=1234567890000&endTime=1234567900000
- **THEN** 接口 SHALL 返回设备 xxx 在指定时间范围内的所有历史记录

#### Scenario: 组合筛选（事件ID + 时间范围）
- **WHEN** 请求 GET /device/history/api/filter?deviceNo=xxx&eventIds=1&startTime=1234567890000&endTime=1234567900000
- **THEN** 接口 SHALL 返回设备 xxx 在指定时间范围内的 eventId 为 1 的记录

#### Scenario: 限制返回数量
- **WHEN** 请求 GET /device/history/api/filter?deviceNo=xxx&limit=10
- **THEN** 接口 SHALL 返回设备 xxx 的最多 10 条历史记录

#### Scenario: 无参数（返回全部）
- **WHEN** 请求 GET /device/history/api/filter?deviceNo=xxx
- **THEN** 接口 SHALL 返回设备 xxx 的所有历史记录（不超过默认 limit）

#### Scenario: 无效设备号
- **WHEN** 请求 GET /device/history/api/filter?deviceNo=
- **THEN** 接口 SHALL 返回 HTTP 400 错误，提示 "deviceNo 不能为空"

#### Scenario: 不存在的设备号
- **WHEN** 请求 GET /device/history/api/filter?deviceNo=nonexistent
- **THEN** 接口 SHALL 返回空列表，不报错

#### Scenario: 无效事件ID
- **WHEN** 请求 GET /device/history/api/filter?deviceNo=xxx&eventIds=99999
- **THEN** 接口 SHALL 返回空列表，不报错

### Requirement: API 返回格式
接口返回的 JSON 格式 SHALL 与现有 `/device/history/api/list` 接口的 list 字段格式一致。

#### Scenario: 返回格式一致性
- **WHEN** 调用 /device/history/api/filter 接口
- **THEN** 返回的 list 数组中每个元素 SHALL 包含 id、deviceNo、eventId、eventName、eventNumber、eventUnit、startTime、endTime、remark 字段
- **AND** 字段类型 SHALL 与 /device/history/api/list 接口一致
