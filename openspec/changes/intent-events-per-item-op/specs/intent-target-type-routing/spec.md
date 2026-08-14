## ADDED Requirements

### Requirement: feeding 与 history 依赖 events，conversation/exit 不依赖
当 `target_type` 为 `feeding` 时，系统 SHALL 要求非空 `events` 且子项 `op` 属于喂养写路径（`create|update|delete|end`）方可进入落库准备。当 `target_type` 为 `history` 时，系统 SHALL 要求非空 `events` 且含 `op=read`（或等价投影）方可进入查记录。当 `target_type` 为 `conversation` 或 `exit` 时，系统 MUST NOT 因 `events` 为空而失败。

#### Scenario: feeding 无 events 不得落库
- **WHEN** `target_type=feeding` 且 `events` 为空
- **THEN** 系统 MUST NOT 调用历史 batch 落库

#### Scenario: history 经 events 读
- **WHEN** `target_type=history` 且 `events` 含带窗口的 `op=read` 项
- **THEN** 系统 SHALL 按子项执行查记录路径

#### Scenario: exit 直接结束
- **WHEN** `target_type=exit`
- **THEN** 图 SHALL 可结束会话语义
- **AND** MUST NOT 要求 `events` 非空
