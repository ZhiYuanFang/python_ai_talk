## ADDED Requirements

### Requirement: Record confirm messages include inferred time slots

当需要用户确认的喂养意图为记录类（`create` / `start` / `end`，含多事件中的对应子项）时，系统 SHALL 根据将落库的 `start_time` / `end_time`（Unix，Asia/Shanghai 语义）与可选 `quantity` 生成口语化 `confirm_message`。日段与相对日（今天/昨天/昨晚等）MUST 由时间戳相对「现在」反推，MUST NOT 以回放用户原话中的日段词作为确认文案的权威来源。单事件与多事件 SHALL 使用同一套槽位格式化逻辑。

#### Scenario: Instant with clock and quantity

- **WHEN** 用户意图为记录配方奶，子项带 `quantity=120` 与有效 `start_time`（例如当天早上 8 点）
- **AND** 需要确认
- **THEN** `confirm_message` SHALL 点出事件名、数量与可读时间（含反推日段或等价口语），语义接近「记录早上 8 点吃了 120 毫升配方奶」

#### Scenario: Closed interval

- **WHEN** 子项为睡眠且 `end_time` > `start_time`（例如当天 10 点到 12 点）
- **AND** 需要确认
- **THEN** `confirm_message` SHALL 读出起止时间与事件名，语义接近「记录早上 10 点到 12 点的睡眠」

#### Scenario: Start without explicit clock uses 现在

- **WHEN** 子项为开始睡觉且无有效 `start_time`（或视为「现在」阈值内）
- **AND** 需要确认
- **THEN** `confirm_message` SHALL 包含「现在」与开始语义，语义接近「现在开始睡觉」

#### Scenario: Record without time uses 现在

- **WHEN** 子项为记录洗澡且无有效时间槽
- **AND** 需要确认
- **THEN** `confirm_message` SHALL 包含「现在」与记录语义，语义接近「现在记录洗澡」

#### Scenario: Multi-event still per-item slots

- **WHEN** 需要确认且 `events` 长度大于 1，各子项带各自时间或数量
- **THEN** `confirm_message` SHALL 逐项体现各子项的时间/数量信息（与单事件同一格式化规则），MUST NOT 退回仅罗列事件名而无量、无时（在子项本有槽位时）

### Requirement: Query and delete confirm copy unchanged by this change

本能力增量 MUST NOT 要求修改查记录确认（`build_history_confirm_message` 或等价）或删除确认（`build_delete_confirm_message` 或等价）的既有句式；记录类时间口语化 MUST NOT 强制套用到查/删路径。

#### Scenario: History confirm still name-focused

- **WHEN** 查记录需要确认
- **THEN** 确认话术 SHALL 仍以查询事件名（及可选备注专名）为主，MUST NOT 仅因本增量而强制改为「现在记录…」句式
