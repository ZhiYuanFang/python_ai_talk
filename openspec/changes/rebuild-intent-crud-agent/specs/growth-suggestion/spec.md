## MODIFIED Requirements

### Requirement: 成长建议接口
系统 SHALL 通过 clinic 陪伴接口（`POST /v1/clinic` 或 `/v1/clinic/stream`）支持成长建议场景，SHALL NOT 再要求意图分析接口以 `target_type=suggest` 走内部 clinic agent 后处理。

#### Scenario: 经 clinic 生成喂养建议
- **WHEN** 调用方对 `/v1/clinic` 发送「宝宝最近食量怎么样」
- **THEN** 系统根据 clinic 数据准备（含历史）生成陪伴/建议文本于 `answer`

#### Scenario: 意图入口不再产出 suggest 结构
- **WHEN** 用户对 `/v1/analyze/intent` 发送同类问题
- **THEN** 系统 SHALL NOT 返回依赖 Go 再调建议链路的 `target_type=suggest` 空 content 结构作为主路径
- **AND** SHALL 按意图图规则给出 conversation 或查记录结果，完整建议由调用方改打 clinic

### Requirement: 历史数据聚合
系统 SHALL 在 clinic 路径根据用户问题使用已拉取的历史数据（含统计口径由生成模型完成），不得为此在意图图恢复 suggest 专用聚合节点。

#### Scenario: 日均喂养量类问题走 clinic
- **WHEN** 用户经 clinic 询问「最近一周宝宝平均每天吃多少」
- **THEN** 回答 SHALL 基于注入的历史，无史时明确不足

### Requirement: LLM 建议生成
系统 SHALL 在 clinic 生成中使用 LLM 结合历史与画像给出自然语言建议；意图路径 MUST NOT 再调用 clinic_answer。

#### Scenario: clinic 生成详细建议
- **WHEN** clinic_graph 完成数据准备并生成
- **THEN** `answer` 为自然语言建议或陪伴说明
