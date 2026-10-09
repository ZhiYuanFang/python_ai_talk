## ADDED Requirements

### Requirement: daily 缺窗时须按日词规则补时间窗
当 `history_mode` 为 `daily`、存在 `op=read`、且相关 read 的有效拉史起止均缺失（0/空）、且 `ignore_time_range` 不为真时，系统在拉史之前 MUST 根据用户原文中的日历日词（至少支持今天/昨日/前天，本周按实现约定）补全 Asia/Shanghai 下的 unix 时间窗并用于 filter。MUST NOT 在用户明确「昨天/今天」等而窗仍缺失时无时间界拉取后冒充该日次数或清单。

#### Scenario: 昨天几次补昨天整日窗
- **WHEN** 用户问「昨天喝了几次水」（或语义等价）
- **AND** 分类为 history + daily + read，但 start/end 无效
- **AND** 用户确认后进入播报拉史
- **THEN** 拉史请求 SHALL 带有对应「昨天」日历日的 startTime/endTime（或等价）
- **AND** MUST NOT 仅用无时间参数的 filter 拉近期多日

#### Scenario: 已有有效窗不覆盖
- **WHEN** daily read 已带非零有效时间窗
- **THEN** 系统 MUST NOT 用日词规则覆盖该窗

### Requirement: 次数问 daily 须显式报次数
当用户原文为次数问（含几次/多少次等实现约定线索）且走 `history_mode=daily` 播报时，用户可见 content MUST 显式包含该查询事件在窗内的发生次数。对 `event_type=number` 的叶子，MUST NOT 仅以「总量{毫升}」回答次数问而不给出次数。

#### Scenario: 昨天喝水几次听到次数
- **WHEN** 用户问「昨天喝了几次水」且 daily 拉史窗内该事件有 1 条记录
- **THEN** content SHALL 体现 1 次（或等价「昨天喝水 1 次」）
- **AND** MUST NOT 仅输出多日【本地摘要】与「总量 xml」而无次数
