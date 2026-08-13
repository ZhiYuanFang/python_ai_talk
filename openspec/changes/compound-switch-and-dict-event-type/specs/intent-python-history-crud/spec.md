## ADDED Requirements

### Requirement: 结束计时只交事件 id 与 action=end
当子项 `action=end` 且目标为字典叶子时，Python 组装 batch 项 SHALL 使用该叶子 `eventId` 与 `op=end`（或等价 `action=end`）。该项的历史行 id MUST 为 0 或不传。系统 MUST NOT 为结束计时先调用 filter/latest 查询进行中记录，MUST NOT 由 Python 填写结束时间。结束最近一条的语义由兄弟仓按 `eventId` 完成。

#### Scenario: 停止爬练习不查进行中
- **WHEN** 已确认意图含爬练习 `action=end` 且字典有该叶子 id
- **THEN** batch 中对应项 SHALL 带该 `eventId` 且 `op` 为 end
- **AND** SHALL NOT 携带非 0 的历史行 id
- **AND** 本请求 MUST NOT 为该 end 项额外调用 latest 或 filter

### Requirement: 落库前按字典事件类型覆盖起止时间
组装 batch 之前，系统 SHALL 按事件字典该叶子的 `event_type` 覆盖子项时间，MUST NOT 使用 LLM 返回的 `event_type`。字典类型不是 `time`（含 `one`、`number` 以及缺省）时，create 项 MUST 设置 `endTime` 等于 `startTime`，MUST NOT 使用 `endTime=0`。字典类型为 `time` 且子项 `action=end` 时走结束项（见上条）。字典类型为 `time` 且子项不是 `end` 时，create 项 MAY 使用 `endTime=0` 表示进行中。

#### Scenario: 一次性不得记成进行中计时
- **WHEN** 叶子字典 `event_type` 为 `one` 或 `number`，且意图为 create
- **THEN** 提交 Go 的该项 `endTime` SHALL 等于该项 `startTime`
- **AND** SHALL NOT 为 0

#### Scenario: 计时开始允许进行中
- **WHEN** 叶子字典 `event_type` 为 `time` 且子项 `action` 为 `start`（或非 end 的记录）
- **THEN** 提交 Go 的该项 SHALL 为 create 且 `endTime` 可为 0

#### Scenario: 缺类型按非计时处理
- **WHEN** 叶子字典缺少 `event_type` 或类型无法识别
- **THEN** create 项 `endTime` SHALL 等于 `startTime`

### Requirement: 同一 batch 中结束项先于新建项
当一次 batch 同时含 `op=end` 与 `op=create` 的子项时，系统 SHALL 在提交前将全部 end 项排在全部 create 项之前。系统 MUST NOT 依赖模型 `events[]` 的原始顺序。

#### Scenario: 停爬并开始坐时先 end
- **WHEN** 已确认 `events[]` 为爬练习 end 与坐练习 start
- **THEN** 提交 Go 的 `items[]` SHALL 先出现爬练习 end，再出现坐练习 create
