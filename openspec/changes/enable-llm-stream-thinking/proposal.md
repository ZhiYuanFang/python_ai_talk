## Why

Clinic/tip 已传 `thinking_enabled=True` 并转发 `LLMResponse.thinking`，但客户端从未真正打开 DeepSeek/智谱的原生思考模式，只靠在 `content` 里抠 `[思考]`，流式下几乎总是空。前端体感只剩编排节点固定字幕。需要把提供商原生 `reasoning_content` 稳定填进 `thinking`，并按产品约定区分两类 thinking 的换行：编排字幕末尾补 `\n`，LLM 思考增量末尾不加。

## What Changes

- `thinking_enabled=True` 时，对 **deepseek** 与 **glm/zhipu** 流式请求真正打开思考模式（如 `extra_body={"thinking": {"type": "enabled"}}`）。
- 流式 chunk：将提供商 `reasoning_content`（或等价字段）映射到 `LLMResponse.thinking`，`content` 只承载正文；同一 chunk 可同时产出两者，不做互斥丢弃。
- 降级/删除「从正文里抠 `[思考]` / `思考：`」作为主路径；不再依赖提示词强制文本标签。
- **编排阶段 thinking**（`emit_thinking`、图节点字幕、`llm_start` 等）：若文案末尾无换行，补一个 `\n`。
- **LLM 流式 thinking**：原样转发增量，**末尾不加** `\n`。
- SSE 契约不变（仍 `type=thinking` / `answer`）；intent 同步 invoke、Q&A 捷径不在本次范围。

## Capabilities

### New Capabilities

- `llm-native-stream-thinking`: DeepSeek/智谱流式原生思考开关与 `reasoning_content`→`LLMResponse.thinking` 映射；编排 thinking 末尾 `\n`、LLM thinking 不加。

### Modified Capabilities

- （无已归档基线；与既有 clinic/tip SSE thinking 管道对齐由本 change 新 capability 描述。）

## Impact

- `app/shared/llm_client.py`（客户端创建/调用、`stream` 字段映射）
- `app/shared/graphs/node_thinking.py`（`emit_thinking` 末尾换行）
- clinic/tip 路由中编排类 thinking（如 `llm_start`）出口
- 单测：mock chunk 带 `reasoning_content` / 编排换行断言
- API 路径与 SSE 字段名不变；不改编排图结构、提示词闺蜜规则
