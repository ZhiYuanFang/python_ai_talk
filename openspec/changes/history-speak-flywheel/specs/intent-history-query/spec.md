## MODIFIED Requirements

### Requirement: 点查上次优先已完成记录
对「上一次/上次/最近一次」类点查（`op=read` 且忽略或等价点查窗），系统在候选历史中选答时 SHALL **服从查史播报策略维** `point_pick`（来自独立飞轮或查史播报小 LLM，见 `intent-history-speak-flywheel`）。当且仅当 `point_pick=prefer_completed` 时，系统 SHALL 跳过无有效 `endTime` 的进行中记录、优先采用上一笔已完成记录作答。当 `point_pick=latest` 时，系统 SHALL 按开始时间取最近一条（进行中可胜出），MUST NOT 在存在更新的进行中行时仍强制答更早已完成。缺维时 MUST NOT 静默等同本要求的旧「无条件优先已完成」行为。

#### Scenario: prefer_completed 时进行中之上答上一笔完成
- **WHEN** `point_pick=prefer_completed` 且用户点查某计时事件
- **AND** 最新一行为进行中，且更早存在已完成记录
- **THEN** `content` SHALL 基于该已完成记录作答
- **AND** SHALL NOT 把进行中行的开始时间说成上一次发生时间

#### Scenario: latest 时答最近进行中
- **WHEN** `point_pick=latest` 且最新一行为进行中、更早有已完成
- **THEN** `content` SHALL 基于该进行中行作答（话术再服从 `open_speak`）

#### Scenario: prefer_completed 且仅有进行中一条
- **WHEN** `point_pick=prefer_completed` 且该事件筛选结果仅有一条进行中、无已完成
- **THEN** `content` SHALL 按 `open_speak` 播报进行中（`in_progress` 时可为「目前仅找到一条记录…正在进行中」形式；`elapsed` 时为已持续时长）

### Requirement: 父事件点查同样跳过进行中
父事件点查展开子孙叶子后，取「最近」时 SHALL 同样服从 `point_pick`：`prefer_completed` 时跳过进行中行并在已完成中取最近；`latest` 时按开始时间取最近（进行中可胜出）。若选中为进行中，SHALL 按 `open_speak` 播报，并可点出父名与叶子名。

#### Scenario: 父事件下 prefer_completed 且最新为进行中
- **WHEN** `point_pick=prefer_completed` 且用户点查父事件，子孙中最新为进行中、另有已完成
- **THEN** `content` SHALL 基于已完成记录作答并点出父名与对应叶子名

#### Scenario: 父事件下 latest 且最新为进行中
- **WHEN** `point_pick=latest` 且子孙中开始时间最近为进行中
- **THEN** `content` SHALL 基于该进行中行作答（服从 `open_speak`）
