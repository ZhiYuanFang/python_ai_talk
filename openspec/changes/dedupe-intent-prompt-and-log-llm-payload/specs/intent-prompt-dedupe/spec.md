## ADDED Requirements

### Requirement: Intent user message excludes event catalog

意图分类的用户消息 MUST 仅包含用户输入与分析指令，MUST NOT 再次嵌入可用事件名称列表或事件字典。事件目录 MUST 仅通过系统提示词注入（含 event id 与 name）。

#### Scenario: User message has no event list

- **WHEN** 意图分类节点构建 LLM 用户消息
- **THEN** 用户消息 SHALL 包含待分析的用户输入文本
- **AND** SHALL NOT 包含「可用事件类型」或等价事件名/事件目录 JSON 列表

#### Scenario: System prompt still carries event catalog

- **WHEN** 意图分类节点构建系统提示词且事件字典非空
- **THEN** 系统提示词 SHALL 包含可用事件的 id 与 name
