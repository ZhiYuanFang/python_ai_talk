## ADDED Requirements

### Requirement: Suggest generation does not use suggest_answer module

系统 SHALL NOT 再通过 `suggest_answer` 提示词模块生成 intent suggest 回答；suggest 路径 SHALL 继续由 `call_clinic_agent` / `clinic_answer` 承担（本 change 不改变该路由）。

#### Scenario: suggest_answer module removed

- **WHEN** 代码库完成清理
- **THEN** 仓库中 SHALL NOT 存在被运行时引用的 `suggest_answer` 提示词模块（文件删除或无任何 import）

### Requirement: generate_response serves history only

`generate_response` 节点 SHALL 仅使用 history 回答提示词生成同步回答，SHALL NOT 再按 `target_type == "suggest"` 分支选择建议提示词。

#### Scenario: History short chain still works

- **WHEN** intent 路由到 history 短链并执行 `generate_response`
- **THEN** 系统 SHALL 使用 history_answer 构建提示并返回回答

#### Scenario: No suggest branch in generate_response

- **WHEN** 检查 `generate_response` 实现
- **THEN** 代码中 SHALL NOT 存在选择 `suggest_answer` 或等价 suggest 专用提示词的分支
