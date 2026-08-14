## ADDED Requirements

### Requirement: 意图信封与事件数组分离
意图分析结果 SHALL 使用信封字段表达会话级语义（至少含 `target_type`、`content`、确认相关字段），MUST NOT 再使用顶层 `op` 或顶层 `action` 作为 CRUD/读/多事件开关。凡涉及字典事件的增删改结束或查询，MUST 通过非空 `events` 数组表达；闲聊与退出 MUST NOT 依赖 `events`（`events` 可空或不出现）。

#### Scenario: 闲聊无 events
- **WHEN** `target_type` 为 `conversation`
- **THEN** 响应 MAY 含自然语言 `content`
- **AND** MUST NOT 要求非空 `events` 才能返回成功

#### Scenario: 退出无 events
- **WHEN** `target_type` 为 `exit`
- **THEN** 系统 SHALL 结束会话语义
- **AND** MUST NOT 要求非空 `events`

#### Scenario: 响应无顶层 op/action
- **WHEN** 意图分析返回结构化结果
- **THEN** 权威契约 MUST NOT 要求调用方读取顶层 `op` 或顶层 `action`
- **AND** 涉事件语义 MUST 从 `events[]` 读取

### Requirement: 子项自带 op
`events[]` 每一项 MUST 包含 `op`，取值 MUST 为 `create`、`update`、`delete`、`end` 或 `read` 之一。计时结束 MUST 使用 `op=end`。开始计时或留下新记录 MUST 使用 `op=create`（并可带可选子项 `action` 为 `start` 或 `one`）。修改已有记录 MUST 使用 `op=update`；删除 MUST 使用 `op=delete`；查记录 MUST 使用 `op=read`。系统 MUST NOT 将「结束计时」表示为 `op=update`。

#### Scenario: 复合结束与开始
- **WHEN** 用户要结束睡眠并开始爬练习
- **THEN** `events` SHALL 至少含一项 `op=end` 对应睡眠
- **AND** SHALL 含另一项 `op=create` 对应爬练习（`action` 可为 `start`）
- **AND** MUST NOT 仅用单一顶层字段表达上述两件事

#### Scenario: 单事件也是长度为 1 的 events
- **WHEN** 用户仅开始爬练习
- **THEN** `events` SHALL 长度为 1
- **AND** 该项 `op` SHALL 为 `create`

### Requirement: 查记录子项自带时间窗
当子项 `op=read` 时，该项 SHALL 可携带自己的 `start_time` 与 `end_time`（Unix 秒）以界定拉取窗口，MAY 携带 `remark_keyword`。系统 MUST NOT 要求所有 read 子项共享唯一的顶层时间窗作为唯一权威来源。

#### Scenario: 两项读不同窗
- **WHEN** `events` 含两个 `op=read` 子项且各自 `start_time`/`end_time` 不同
- **THEN** 查记录执行 SHALL 按各子项窗口分别拉取（或等价按项过滤）
- **AND** MUST NOT 强制两子项使用同一顶层时间窗覆盖其自有窗口

### Requirement: 落库按子项 op 执行
确认后的喂养落库 SHALL 将 `events` 中 `op` 为 `create`、`update`、`delete`、`end` 的项组装为一次 Go batch；提交前 MUST 将全部 `end` 项排在非 `end` 项之前。系统 MUST NOT 用已删除的顶层 `op` 覆盖子项。仅当子项 `op` 为 `update` 或 `delete` 时，MAY 按事件现查最近历史 id；`create` 与 `end` MUST NOT 因「找不到可改/删记录」而失败。

#### Scenario: 结束睡眠并开始爬练习落库
- **WHEN** 已确认的 `events` 为睡眠 `end` 与爬练习 `create`
- **THEN** batch SHALL 先提交 end 再提交 create
- **AND** 爬练习 MUST 按新建计时处理
- **AND** MUST NOT 因爬练习无最近记录而跳过 create
