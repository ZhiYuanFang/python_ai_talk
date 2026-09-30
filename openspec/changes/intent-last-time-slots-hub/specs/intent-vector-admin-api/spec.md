## ADDED Requirements

### Requirement: 意图向量列表接口
系统 SHALL 提供管理用 HTTP 接口，列出 `feeding_intents` 中条目，至少包含向量 id、document、quality_score、payload 摘要（或完整 payload）。接口 MUST 需与现有管理/服务间调用约定对齐（如仅内网或管理密钥；具体鉴权与 Go Hub 侧 Admin JWT 配合）。本接口 MUST NOT 写入 MySQL。

#### Scenario: 列出缓存条目
- **WHEN** 管理调用方请求意图向量列表
- **THEN** 响应 SHALL 包含至少一条字段完整的条目结构（库空时可为空列表）
- **AND** SHALL NOT 要求或写入兄弟仓 MySQL

### Requirement: 意图向量批量写入
系统 SHALL 提供批量 upsert 接口：每项含 document 与 payload（含 `target_type`/`events` 等），写入或更新 Chroma `feeding_intents`，质量分默认与运行时写入一致。确认词 document MUST NOT 写入。本接口 MUST NOT 同步 MySQL。

#### Scenario: 批量灌入种子
- **WHEN** 管理方提交两条合法 document+payload
- **THEN** 系统 SHALL 将二者写入或更新 `feeding_intents`
- **AND** 后续用户输入与种子高度相似时 MAY 命中缓存（仍受相似度与质量分门槛约束）

### Requirement: 意图向量按 id 删除
系统 SHALL 提供按向量 id 删除 `feeding_intents` 条目的接口。删除成功后该 id MUST NOT 再参与匹配。本接口 MUST NOT 以 MySQL 成功为前置条件。

#### Scenario: 删除错误种子
- **WHEN** 管理方删除某错误向量 id
- **THEN** 该 document 不得再以该 id 被检索命中
- **AND** 高度相似的错误说法 MUST NOT 再因该条免确认执行（除非仍存在其他匹配条目）
