## ADDED Requirements

### Requirement: 点查必须先定事件且每条带备注
当用户问「上次/什么时候/何时」等点查时，系统 SHALL 在拉史前确定 `event_ids`（分类、缓存或备注探针确认后的字典叶子）。系统 MUST NOT 在点查路径用空 `event_ids` 拉取全类型原始行并注入 prompt 或生成模型。点查返回的每条记录 MUST 包含时间、用量或时长（若有）以及备注（空则省略）。播报 SHALL 使用模板，MUST NOT 再调用历史答题 LLM。

#### Scenario: 已知事件点查
- **WHEN** 用户问「上一次拉屎是什么时候」且分类给出该事件 `event_id` 与 Unix 时间窗
- **THEN** 系统 SHALL 仅按该 `event_id` 调用 filter
- **AND** `content` SHALL 用模板给出最近一条的时间（有备注则带上）
- **AND** SHALL NOT 调用 `judge_data_requirement` 或历史生成 LLM

#### Scenario: 点查禁止全事件原始行
- **WHEN** 点查意图的 `event_ids` 为空且备注探针亦未定出唯一或待确认事件
- **THEN** 系统 SHALL 确认或说明无法确定事件
- **AND** MUST NOT 把该设备窗口内全部原始 history 行注入 prompt

### Requirement: 日汇总必须先压缩
当用户问整天、趋势或无法在分类阶段定事件时，系统 MAY 按时间窗拉取多类型记录，但 MUST 立即压缩为按日 `{事件名}+{备注}：用量/时长/次数`，MUST NOT 把原始 list 交给生成模型或塞进意图分类 prompt。

#### Scenario: 整天问法只注入压缩摘要
- **WHEN** 用户问「今天吃了什么」且走日汇总
- **THEN** 注入或播报的数据 SHALL 为压缩摘要
- **AND** SHALL NOT 为原始 history JSON 数组

### Requirement: 时间窗使用 Unix 秒
查记录的 `startTime`/`endTime` SHALL 为 Unix 秒。分类提示词 SHALL 注入当前上海时区墙钟与 unix。Python 拉史 SHALL 校验并夹紧窗口，MUST NOT 再把 `today|yesterday|last_7_days` 等枚举自行换算为起止时间。clinic、tip、care-alert 调用共享拉史时 SHALL 传入已计算的 unix，MUST NOT 再传上述枚举。

#### Scenario: 分类给出 unix 窗
- **WHEN** 用户问「昨天喝了多少奶」
- **THEN** 拉史请求的 startTime/endTime SHALL 为昨天上海时区对应的 Unix 秒
- **AND** SHALL NOT 依赖 `time_range=yesterday` 映射函数

### Requirement: 多事件点查分别说明
当点查包含多个 `event_ids` 时，系统 SHALL 按事件分别模板播报最近一条或明确「没有记到 X」。

#### Scenario: 两事件分别回答
- **WHEN** 用户问「上一次睡觉拉屎分别在什么时候」且两事件均有记录
- **THEN** `content` SHALL 分别给出两事件最近时间
- **AND** 若其中一件无记录 SHALL 明确说没有记到该事件
