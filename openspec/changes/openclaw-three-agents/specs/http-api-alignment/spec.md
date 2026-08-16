## ADDED Requirements

### Requirement: filter 按 start_time 倒序
`GET /device/history/api/filter`（及 Python `get_filtered_history_events` 消费方）在用于点查取前 k 条时，SHALL 以事件发生时间 `start_time`（或等价列）**降序**作为主排序。系统 MUST NOT 仅依赖 `id DESC` 作为「前 k 次发生」的权威顺序（若 id 与 start_time 不一致）。

#### Scenario: 返回顺序时间倒序
- **WHEN** filter 对某 eventId 返回多条记录且未忽略业务排序
- **THEN** 列表中靠前的记录 MUST 具有不早于靠后记录的 start_time（降序）

### Requirement: Intent 停止经 batch 落库
Python Intent 落库主路径 SHALL 调用 create/update/delete/end 单动词接口（见 `agent-business-tool-contract`），MUST NOT 再调用 `POST .../event/batch` 作为意图确认后的写入口。

#### Scenario: http_client 意图写不走 batch
- **WHEN** Intent 确认后执行历史写入
- **THEN** 发出的写请求 MUST 为单动词 REST
- **AND** MUST NOT 以 event/batch 作为该路径唯一写入口
