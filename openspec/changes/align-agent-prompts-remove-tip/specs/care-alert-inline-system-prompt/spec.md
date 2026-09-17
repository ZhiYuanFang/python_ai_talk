## ADDED Requirements

### Requirement: Care-alert system prompt is inlined from former prompt.json

护理留意分析的 system 提示词 SHALL 以内联代码常量提供，内容 MUST 以变更实施时仓库中 `data/care_alert/prompt.json` 的 `output_format`（及必要 guidance）为准迁入，并 SHALL 追加内部思考须使用中文的约束。系统 MUST NOT 再通过 `prompt_store.load_or_bootstrap_prompt` 从磁盘加载 system。

#### Scenario: Analyze does not read prompt.json

- **WHEN** 执行 care_alert analyze（同步或流式）
- **THEN** 构建 system 提示词 MUST NOT 依赖存在 `data/care_alert/prompt.json`

#### Scenario: Production wording preserved

- **WHEN** 对比迁入后的 system 常量与实施前 `prompt.json` 的 `output_format`
- **THEN** 判定口径与输出 JSON schema 要求 SHALL 实质一致（允许仅增加中文思考等约束句）
