## ADDED Requirements

### Requirement: 管理端重复以 document 原文全等为准
系统 SHALL 将管理端「重复」定义为：两条意图缓存的 `document` 在去除首尾空白后字符串完全相等。系统 MUST NOT 仅凭 embedding 相似度或 payload 字段判定管理端重复。

#### Scenario: 文案相同即重复
- **WHEN** 两条条目的 document 去首尾空白后均为「宝宝喝了奶」
- **THEN** 系统 SHALL 视二者为重复，无论 payload 或 quality_score 是否不同

#### Scenario: 文案不同不重复
- **WHEN** 两条 document 分别为「宝宝喝了奶」与「宝宝喝奶了」
- **THEN** 系统 MUST NOT 因语义相近而在管理端将其视为重复

### Requirement: 管理 bulk 跳过已有相同 document
管理端批量写入接口对已存在于 `feeding_intents` 中、或同批请求内已处理过的相同 document（按上条定义）MUST **跳过**写入，MUST NOT 覆盖已有条目的 payload 或 quality_score。新 document 仍 MUST 写入。确认词与空句 MUST NOT 写入，并计入失败或等价未写入说明。响应 MUST 区分新增与跳过（至少包含可枚举的 skipped 条目，含 document；宜含 index / existing_id），供管理 UI 展示。

#### Scenario: 库中已有同文案则跳过
- **WHEN** 库中已有 document「宝宝喝了奶」，管理方 bulk 再提交同 document 的种子
- **THEN** 系统 MUST NOT 更新该条
- **AND** 响应 SHALL 将该项列入 skipped（或等价字段）

#### Scenario: 新文案仍写入
- **WHEN** 管理方 bulk 提交库中不存在的 document「宝宝吃了辅食」及合法 payload
- **THEN** 系统 SHALL 将其写入 `feeding_intents`
- **AND** 响应 SHALL 体现新增成功

#### Scenario: 同批内重复只落一条
- **WHEN** 单次 bulk 请求中连续两项 document 去空白后相同
- **THEN** 系统 SHALL 至多写入一条
- **AND** 其余 SHALL 列入 skipped

### Requirement: 管理端整理重复 document
系统 SHALL 提供管理接口，扫描 `feeding_intents`，将 document 去空白后相同的条目归为一组；每组 MUST 保留恰好一条，并删除其余。保留规则 MUST 优先较高 `quality_score`，同分 MUST 优先较早 `created_at`，再同分 MUST 以稳定次序（如 id 字典序）打破平局。响应 MUST 列出被删除条目（至少 id 与 document），供管理 UI 弹窗展示。本接口 MUST NOT 写入 MySQL。

#### Scenario: 三份同文案删其二
- **WHEN** 库中存在三条 document 均为「喝水」的条目且管理方触发整理重复
- **THEN** 系统 SHALL 仅保留一条
- **AND** 响应 SHALL 包含两条被删记录的 id 与 document

#### Scenario: 无重复时不删
- **WHEN** 库中所有 document 去空白后互不相同且管理方触发整理重复
- **THEN** 系统 MUST NOT 删除任何条目
- **AND** 响应中的 deleted 列表 SHALL 为空
