## ADDED Requirements

### Requirement: Vector metadata stores English action codes

系统写入喂养事件向量（标准条目与用户表达）时，`metadata.action` SHALL 使用英文 IntentAction 真值（`start`/`end`/`one` 或空字符串表示无动作）；MUST NOT 将「开始」「结束」「记录」写入 `metadata.action`。

#### Scenario: Standard action variants use English ids and metadata

- **WHEN** 系统为事件生成标准动作变体并写入向量库
- **THEN** 变体记录的 `metadata.action` SHALL 为 `start`、`end` 或 `one`
- **AND** 变体记录 id SHALL 使用英文动作片段（如 `std_{event_id}_start`），MUST NOT 使用「开始」等中文片段

#### Scenario: Embedding document may use Chinese surface text

- **WHEN** 系统为标准动作变体生成 embedding 文档文本
- **THEN** document 可以使用中文表面语料（例如与事件名拼接的开始/结束/记录表述）
- **AND** 该中文语料 MUST NOT 定义在 `app/shared/constants.py` 中作为协议枚举值

### Requirement: Vector match returns English action from metadata

系统从向量匹配构造意图结果时，出站 `action` SHALL 直接取自 `metadata.action`（空则默认 `one`），且写入路径已保证其为英文 IntentAction。系统 MUST NOT 实现遗留中文 action 的读路径归一化。

#### Scenario: High-confidence vector match with start variant

- **WHEN** 用户输入匹配到标准变体且该变体 `metadata.action` 为 `start`
- **THEN** 意图结果中的 `action` SHALL 为 `start`

#### Scenario: Empty metadata action defaults to one

- **WHEN** 向量匹配命中记录且 `metadata.action` 为空
- **THEN** 意图结果中的 `action` SHALL 为 `one`

### Requirement: ENV-gated one-shot standard rebuild

系统 SHALL 提供环境变量开关（默认关闭），用于一次性清除并重建所有 `source=standard` 的喂养事件向量；重建 MUST 保留 `source=user` 记录。

#### Scenario: Rebuild disabled by default

- **WHEN** 未设置重建开关或开关为 false，且向量库已有记录
- **THEN** 启动预热 MUST NOT 仅因发版而全量删除并重建 standard 条目

#### Scenario: Rebuild enabled after dictionary fetch succeeds

- **WHEN** 重建开关为 true，且系统已成功获取事件字典（叶子列表）
- **THEN** 系统 SHALL 删除现有 `source=standard` 记录并按当前英文动作编码重新写入标准条目与变体
- **AND** `source=user` 记录 SHALL 被保留

#### Scenario: Rebuild does not delete when dictionary fetch fails

- **WHEN** 重建开关为 true，但事件字典获取失败或为空
- **THEN** 系统 MUST NOT 删除现有 standard 向量
- **AND** SHALL 记录错误日志
