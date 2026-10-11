## ADDED Requirements

### Requirement: 类型向量列表接口
系统 SHALL 提供管理用 HTTP 接口列出类型关键字集合（如 `feeding_type_cues`）中的条目，至少包含向量 id、document、payload 摘要（含 `target_type`/`op`/`history_mode`）。接口鉴权与事件短说法 admin 同级（内网调用）。本接口 MUST NOT 写入 MySQL。

#### Scenario: 分页列出类型关键字
- **WHEN** 管理端请求类型向量列表
- **THEN** 响应 SHALL 含 items 与分页信息
- **AND** 每项 SHALL 可区分 document 与类型 payload

### Requirement: 类型向量批量写入
系统 SHALL 提供批量 upsert 接口：每项含 document 与类型 payload（`target_type`/`op`/`history_mode`）。对已存在相同 document（规范化规则与事件侧一致）MUST **跳过**而非覆盖。确认词与空句 MUST NOT 写入。响应 MUST 区分新增与跳过。本接口 MUST NOT 写入 MySQL。

#### Scenario: 新关键字写入
- **WHEN** bulk 提交 document「多久了」与 history+read payload 且库中无同 document
- **THEN** 系统 SHALL 将其写入类型集合

#### Scenario: 同 document 跳过
- **WHEN** bulk 提交已存在的 document
- **THEN** 系统 SHALL 跳过该条并在响应中计入 skipped
- **AND** MUST NOT 覆盖已有 payload

### Requirement: 类型向量整理重复与删除
系统 SHALL 提供整理重复接口：相同规范化 document 每组保留一条（保留规则对齐事件侧：较高质量分、较早创建等）。系统 SHALL 提供按向量 id 删除接口。删除后该 id MUST NOT 再参与 TYPE 匹配。

#### Scenario: 去重删除多余
- **WHEN** 管理端调用类型向量 dedupe 且存在重复 document
- **THEN** 响应 SHALL 列出被删除条目
- **AND** 每组 MUST 仅保留一条

#### Scenario: 按 id 删除
- **WHEN** 管理端删除某类型向量 id
- **THEN** 后续 TYPE 匹配 MUST NOT 再命中该 id
