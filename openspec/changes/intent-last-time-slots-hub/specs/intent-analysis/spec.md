## ADDED Requirements

### Requirement: 同叶多时刻喂养拆成多条 create
当用户一句话中陈述多次喂养（含不同钟点与/或数量，事件可为同一字典叶子或不同叶子）时，意图分类 SHALL 输出多条 `events[]`，每条 `op=create`（瞬时喂养一般为 `action=one`），并为其填写对应的 `quantity` 与 `start_time`（Unix 秒，Asia/Shanghai 语义）。系统 MUST 允许同一 `event_id` 在同一轮 `events` 中出现多次。系统 MUST NOT 将多次喂养默默合并为一条并用当前时间落库。

#### Scenario: 三时刻配方奶与母乳
- **WHEN** 用户输入「记录今天5点吃了120配方奶，7点吃了150，8点吃了60毫升母乳」且走分类路径
- **THEN** `events` 长度 SHALL 为 3
- **AND** 其中两条可为同一配方奶 `event_id`（数量 120 与 150，start_time 分别对应今日 5 点与 7 点）
- **AND** 一条为母乳（数量 60，start_time 对应今日 8 点）

### Requirement: create 提示词允许填写 start_time
分类 system 提示 MUST 说明：`events[].start_time` / `end_time` 不仅用于 `op=read`，在用户说出具体钟点的 create 时也须填写；瞬时 create 的 `end_time` 可与 `start_time` 相同。

#### Scenario: 提示约束存在
- **WHEN** 维护或加载意图分类 system 提示
- **THEN** 文案 SHALL 含 create 场景填写钟点时间的说明
- **AND** SHALL 含「一句多次喂养对应多条 events」的说明或等价示例
