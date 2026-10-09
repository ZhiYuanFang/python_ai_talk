## ADDED Requirements

### Requirement: 计量语义与计时叶子冲突时改选近义计量叶
当意图分类（LLM）识别到用户表达了数量 `quantity`（如毫升），且按口语名称会落到或倾向于字典中 `type=time` 的叶子时，分类 MUST 在可用事件表中判断是否存在语义近义的 `type=number` 叶子。若存在，该子项的 `event_id` 与 `event_name` MUST 填写该计量叶子（不得编造表外 id），MUST NOT 将带 `quantity` 的 create 目标直接定为该计时叶子。近义关系由模型根据表内名称与 type 判断。当用户表达的是时长（如「N分钟」）而非 `quantity` 时，本 Requirement MUST NOT 强制改选计量叶。当表内不存在近义 `number` 叶时，系统 MAY 保持计时叶并按既有确认路径处理，MUST NOT 编造事件。

#### Scenario: 六十毫升母乳改选瓶喂母乳
- **WHEN** 事件表含计时叶「母乳」与计量叶「瓶喂母乳」（或语义等价近义计量叶）
- **AND** 用户说「记录60毫升母乳」（或语义等价）
- **AND** 走意图分类 LLM 路径（非缓存免确认命中）
- **THEN** 分类结果中对应 create 子项 SHALL 使用计量叶「瓶喂母乳」（或表内该近义 number 叶）的 id 与名称
- **AND** MUST NOT 以计时叶「母乳」作为该带 quantity 的 create 目标
- **AND** `quantity` SHALL 为 60（或语义等价）

#### Scenario: 母乳十分钟仍走计时
- **WHEN** 用户说「母乳10分钟」且未表达毫升等 quantity
- **THEN** 分类 MAY 使用计时叶「母乳」并按计时闭合/开表语义处理
- **AND** MUST NOT 仅因本 Requirement 改选计量叶

### Requirement: 冲突改选须给出简洁确认问句
当分类因上一 Requirement 将目标改选为近义 `number` 叶时，分类产出的 `confirm_message` MUST 为简洁中文确认问句，明确点出该计量叶名称与数量（若有），语义接近「您是要记录{计量叶名}{quantity}毫升嘛？」。`confirm_message` MUST 力求简洁，禁止冗长解释或多选项列表。内部思考（reasoning）MUST 使用中文，并体现对叶子 type 与近义计量叶的核对。

#### Scenario: 确认问句建议瓶喂毫升
- **WHEN** 分类已将「60毫升母乳」改选为「瓶喂母乳」且 quantity=60
- **THEN** `confirm_message` SHALL 简洁询问是否记录瓶喂母乳 60 毫升（或语义等价短句）
- **AND** MUST NOT 仅输出对计时「母乳」的确认问句
