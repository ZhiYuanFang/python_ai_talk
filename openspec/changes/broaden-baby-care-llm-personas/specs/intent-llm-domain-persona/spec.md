## ADDED Requirements

### Requirement: 意图 LLM 人设覆盖宝宝照护记录域
feeding 意图相关维 LLM 的 system 人设（含 OP、事件、时间、数量、形态、备注、分句、查史播报策略、pending 澄清，以及预测两维与定位策略等内联人设）SHALL 以宝宝照护记录为领域表述，MUST NOT 将领域表述为仅限「母婴喂养」或仅喂养。人设 SHALL 可体现领域包含喂养、睡眠、换尿布、营养品、疫苗等可落库事件（具体事件以事件表为准）。

#### Scenario: OP 人设非仅喂养
- **WHEN** 系统组装 OP 轨（顶层轨）system 提示
- **THEN** 人设 SHALL 使用宝宝照护记录类表述
- **AND** MUST NOT 仅写「母婴喂养意图」作为唯一领域标签

### Requirement: other 边界不得以非喂养误伤照护记录
OP 轨语义纠偏中，将用户判为 `other` 的说明 MUST 基于「与宝宝照护记录无关」，MUST NOT 使用「非喂养」作为 other 的充分条件。换尿布、营养品、疫苗等照护落库口语 MUST NOT 仅因非喂养语义被纠偏为 other。

#### Scenario: 换尿布类口语不因非喂养进 other
- **WHEN** 用户段为「换尿布了」且无强制确认覆盖
- **THEN** OP 提示纠偏 SHALL NOT 要求仅因非喂养而判 other
- **AND** 合法落库意图 SHALL 可走 create（或其它非 other 轨，由整体定轨规则决定）
