## ADDED Requirements

### Requirement: 终局无法回答前落问答收件箱
当意图路径即将向用户返回终局失败类回复（至少包括无法识别对应事件、暂不支持类 other、以及实现清单中的其它终局失败；不含仍可续聊的确认/消歧中状态）时，系统 SHALL 在发出该回复之前（或同一处理步内）将一条覆盖缺口记录写入独立收件箱。记录 MUST 至少包含：用户原话、系统失败回复文案、设备或用户侧标识（如 `device_no`）、时间戳；MAY 含 `conversation_id` 与失败类别。该收件箱 MUST NOT 使用规则缺口（`rule_gaps`）或时间飞轮（`feeding_time_cues`）作为存储。

#### Scenario: 无法识别事件写入 miss inbox
- **WHEN** 系统因事件无法对齐而返回「无法识别对应的事件…」类终局文案
- **THEN** 收件箱 SHALL 新增一条含该原话与该回复的记录
- **AND** MUST NOT 将该条写入 time 飞轮集合

#### Scenario: 确认中不写 miss inbox
- **WHEN** 系统仅返回软确认或消歧问句、会话仍可续聊
- **THEN** 系统 MUST NOT 因此写入覆盖缺口收件箱

### Requirement: Hub 可查删覆盖缺口
系统 SHALL 提供管理 API（或等价）供 Hub 分页列出与删除（或标记关闭）覆盖缺口记录。列表 MUST 支持按时间新→旧查看；删除 MUST 使记录不再出现在默认列表中。

#### Scenario: 列出与删除
- **WHEN** Hub 调用列出接口
- **THEN** 返回的记录 SHALL 含原话与失败回复等约定字段
- **WHEN** Hub 删除某条记录
- **THEN** 后续默认列表 MUST NOT 再包含该条
