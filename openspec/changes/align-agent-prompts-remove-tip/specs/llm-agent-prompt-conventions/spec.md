## ADDED Requirements

### Requirement: Each LLM agent module has prompts/system.py

每个对外或共享的 LLM agent 模块（至少含 `growth_trajectory`、`care_alert`、`clinic`、`feeding`、以及 `shared` 中承载 needs_history / data_requirement 提示词的包）SHALL 在 `graphs/nodes/prompts/system.py`（或 shared 等价路径）提供模块级 system 提示词常量。系统 MUST NOT 再为这些 agent 依赖外置可写 `prompt.json` 飞轮文件作为 system 唯一来源。

#### Scenario: Care-alert system is a code constant

- **WHEN** care_alert 分析构建 system 提示词
- **THEN** 文案 SHALL 来自 `care_alert/.../prompts/system.py` 常量，而非读取 `data/care_alert/prompt.json`

#### Scenario: Shared judges use system.py constants

- **WHEN** `judge_needs_history` 或 `judge_data_requirement` 调用 LLM
- **THEN** 其 system 提示词 SHALL 引用 `shared/.../prompts/system.py` 中的常量

### Requirement: Chinese internal thinking and user-facing output

各模块 `system.py` 中的 system 提示词 SHALL 明确要求：内部思考（reasoning）使用中文；面向家长的自然语言与面向产品的结构化中文字段（如选项文案、摘要）使用中文。

#### Scenario: System prompt text includes Chinese-thinking constraint

- **WHEN** 读取任一存活 agent 的 `system.py` 主 system 常量
- **THEN** 正文 SHALL 包含要求内部思考（reasoning）使用中文的明确约束

### Requirement: External streaming APIs must stream the LLM

对客户端暴露的 SSE 或等价流式 HTTP 接口，用于生成主回答（或主 JSON 结果且对外推 thinking）的 LLM 调用 MUST 使用 `llm_client.stream`（或项目统一流式封装）。系统 MUST NOT 在此类接口上先 `invoke` 取得全文再伪装为 token/增量流。内部短判定（意图分类、needs_history、data_requirement、澄清解析等）MAY 使用 `invoke`。

#### Scenario: Clinic stream uses LLM stream

- **WHEN** 客户端调用 clinic 流式接口生成回答
- **THEN** 主回答路径 SHALL 经 `llm_client.stream`（或等价）产出增量

#### Scenario: Internal classify may invoke

- **WHEN** 意图分类节点调用 LLM
- **THEN** MAY 使用 `invoke`，且 MUST NOT 因此违反对外流式接口的 stream 要求

### Requirement: Conventions documented in openspec/project.md

上述 system.py 布局、中文思考、对外流式真 stream 约定 SHALL 写入 `openspec/project.md`（全局约束），并在 `AGENTS.md` 作摘要，供后续新建 agent 遵守。

#### Scenario: Project.md contains LLM agent section

- **WHEN** 阅读 `openspec/project.md`
- **THEN** SHALL 存在描述 LLM agent 提示词与流式约定的章节
