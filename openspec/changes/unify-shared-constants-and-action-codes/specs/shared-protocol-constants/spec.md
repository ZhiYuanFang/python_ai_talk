## ADDED Requirements

### Requirement: Shared English protocol constants

系统 SHALL 在 `app/shared/constants.py` 中以英文定义意图与澄清相关协议枚举值，且该文件 MUST NOT 包含中文 label 或展示文案。

#### Scenario: Constants module defines IntentAction

- **WHEN** 开发者查看 `app/shared/constants.py`
- **THEN** 文件中 SHALL 包含喂养/意图对外动作枚举（至少包括 `start`、`end`、`one`、`reply`、`multi` 及契约已有的其它 IntentAction 值）
- **AND** 文件中 MUST NOT 出现用于协议值的中文「开始」「结束」「记录」

#### Scenario: Code references constants instead of literals for protocol fields

- **WHEN** 业务代码设置或比较 `IntentResponse.action`、`target_type`、`match_source`、向量 `source`、或 `confirm_type` 等协议枚举
- **THEN** 实现 SHALL 使用 `app.shared.constants` 中的定义，而非散落的魔法字符串（测试夹具与 LLM prompt 模板中的示例 JSON 可除外，但出站组装路径 MUST 使用常量）

### Requirement: IntentResponse action field means intent action only

系统 SHALL 保证对外响应字段 `action` 仅表示意图动作（IntentAction），澄清会话状态 MUST 通过 `need_confirm` 与 `confirm_type` 表达，不得用 `disambiguate` 占用 `action`。

#### Scenario: Pending clarification response keeps feeding action

- **WHEN** 系统因父事件消歧或叶子确认返回 pending 澄清响应
- **THEN** `need_confirm` SHALL 为 `true`
- **AND** `confirm_type` SHALL 为 `parent_disambiguation` 或 `leaf_confirm`
- **AND** 顶层 `action` SHALL 等于该 pending 保存的喂养动作（如 `start`/`end`/`one`），MUST NOT 为 `disambiguate`

#### Scenario: Resolve operations do not become IntentResponse.action

- **WHEN** 澄清解析产生内部操作（如 confirm、select、correct、reject、ask_again、new_intent）
- **THEN** 这些值 MUST NOT 作为成功落叶子时的 `IntentResponse.action`
- **AND** 成功落到叶子时 `IntentResponse.action` SHALL 为 pending 中保存的 IntentAction
