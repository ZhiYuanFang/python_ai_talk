## ADDED Requirements

### Requirement: 分类须产出查史模式 history_mode
当 `target_type` 为 `history` 且 `events` 含 `op=read` 时，分类产出 MUST 包含顶层 `history_mode`，取值仅为 `point` 或 `daily`。系统提示 MUST 约束选用规则：点查「上次/上一次/最近一次」等用 `point` 且相关子项 `ignore_time_range=true`；区段内次数、合计、日清单、相邻日事实对比等用 `daily`，子项 `ignore_time_range=false` 并填写对应时间窗。`feeding` CRUD 场景 `history_mode` 可空或不写。

#### Scenario: 今天几次走 daily
- **WHEN** 用户问「今天喂了几次母乳」（或语义等价的区间次数）
- **AND** 走意图分类
- **THEN** 分类结果 SHALL 为 `target_type=history` 且含 read 子项
- **AND** `history_mode` SHALL 为 `daily`
- **AND** 该 read 子项 `ignore_time_range` SHALL 为 false 并带今日时间窗（或语义等价）

#### Scenario: 上次走 point
- **WHEN** 用户问「上次换尿布是什么时候」
- **AND** 走意图分类
- **THEN** `history_mode` SHALL 为 `point`
- **AND** 相关 read 子项 `ignore_time_range` SHALL 为 true

### Requirement: 养育建议与最近怎么样不走装懂查史
当用户表达养育建议、是否正常、怎么办，或含糊的「最近怎么样」等应归喂养建议（clinic）的语义时，意图分类 MUST NOT 将其分类为依赖历史装建议的 `history` 成功路径；MUST 使用 `target_type=conversation`（events 为空），并给出简短中文引导（指向喂养建议/clinic 能力）。MUST NOT 编造趋势结论或医疗建议。

#### Scenario: 最近怎么样归 conversation
- **WHEN** 用户说「最近怎么样」或语义等价的含糊近况询问（非明确「今天几次/昨天奶量」等事实区段问）
- **AND** 走意图分类
- **THEN** `target_type` SHALL 为 `conversation`
- **AND** `events` SHALL 为空
- **AND** `content` SHALL 引导用户使用喂养建议（clinic）类能力（简洁中文）

#### Scenario: 够不够吃归 conversation
- **WHEN** 用户问「宝宝奶够不够吃」或「这样正常吗」类建议语义
- **THEN** 分类 SHALL 为 `conversation` 并引导 clinic
- **AND** MUST NOT 仅用 point 查史冒充建议答案
