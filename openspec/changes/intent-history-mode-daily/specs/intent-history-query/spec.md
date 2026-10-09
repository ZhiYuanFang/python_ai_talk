## ADDED Requirements

### Requirement: history_mode=daily 由分类驱动区段事实播报
当意图结果 `history_mode` 为 `daily` 且存在 `op=read` 时，`speak_history`（或等价）SHALL 按已有日汇总路径播报：使用共享喂养史紧凑聚合（含时刻流水与总量/次数等总量段，以及窗内相邻日事实增减摘要若有），MUST NOT 回落到「上一次」点查模板。当 `history_mode` 为 `point` 或缺省时，SHALL 保持既有点查/父塌缩模板行为。分类未给出 `history_mode` 但用户语义明显为区间次数/合计时，实现 MAY 在进入播报前纠偏为 `daily`（若采用，须有中文注释说明）。

#### Scenario: 今天几次播日报而非上一次
- **WHEN** 分类产出 history + read + `history_mode=daily` + 今日时间窗
- **AND** 拉史返回该窗内多条喂养记录
- **THEN** 用户可见 content SHALL 为日汇总/紧凑事实播报（可含次数或总量信息）
- **AND** MUST NOT 仅用单条「上一次…」点查句冒充全日次数

#### Scenario: point 模式不受 daily 改写
- **WHEN** `history_mode` 为 `point` 或未设且走点查
- **THEN** 系统 SHALL 继续使用既有点查模板
- **AND** MUST NOT 强制改为 daily 紧凑全文

### Requirement: 区段 daily 拉史 limit 须足够覆盖常见窗
当 `history_mode=daily` 且用户未指定更小 limit 时，系统 SHALL 使用不低于实现约定下限的拉取条数（建议默认至少 50），以降低「本周/近几日」被默认 20 条截断导致次数/合计不全的风险。`point` 模式可继续使用既有默认 limit。

#### Scenario: daily 默认提高 limit
- **WHEN** 播报路径为 daily 且 intent.limit 为空
- **THEN** 拉史请求的 limit SHALL 不低于约定的 daily 默认下限（≥50 或设计文档写明的值）
