## Why

LLM 常在「纯 JSON」输出里夹 `//` / `/* */` 等注释，提示无法杜绝。现有解析只剥 markdown 围栏后直接 `json.loads`，一遇注释整段失败，意图易被误判为闲聊。需要在代码侧先去注释再解析，并在各 LLM JSON 解析点统一接入。

## What Changes

- 在 `shared` 提供去注释 + 加载 LLM JSON 的共用工具（引号内 `//` 等不得误删）。
- 解析管线：去围栏 → 去注释 → `json.loads`（可选再规范化序列化）；失败仍按各调用方既有降级策略。
- 接入意图分类、澄清 LLM、护理留意生成，以及其它对 LLM 原文做 `json.loads` 的共享节点（如 judge_*），避免各写一套。
- 提示词可继续禁止注释（降发生率），**不以提示为唯一防线**。
- **非目标**：本变更不强制做 `op`/`target_type` 字段对齐；不写测试文件；不引入第三方 JSON5 依赖（除非实现极困难再议）。

## Capabilities

### New Capabilities

- `llm-json-parse`: LLM 返回类 JSON 文本的清洗与解析约定（去注释、围栏、安全 loads）。

### Modified Capabilities

- （无强制修改既有 capability 名；行为通过新 capability 约束各解析点。）

## Impact

- **代码**：新建 `app/shared` 工具；改 `classify_intent`、`clarification`、care_alert `_extract_json_object`、`judge_data_requirement` / `judge_needs_history` 等解析入口。
- **行为**：带注释但结构合法的分类/澄清 JSON 可成功解析；真正非法 JSON 仍失败降级。
- **API**：无 HTTP 契约变更。
