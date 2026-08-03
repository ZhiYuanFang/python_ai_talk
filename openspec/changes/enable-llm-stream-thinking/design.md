## Context

Clinic/tip 流式路径已调用 `llm_client.stream(..., thinking_enabled=True)`，路由把非空 `chunk.thinking` 写成 SSE `type=thinking`。但 `thinking_enabled` 目前只触发对 `chunk.content` 的 `[思考]` 文本扫描，请求侧未带 DeepSeek/智谱思考模式参数；LangChain 流式 chunk 上的 `reasoning_content` 也未读取。结果是 LLM 思考通道几乎恒空，前端主要看到 `emit_thinking` / `llm_start` 编排字幕。

提供商（DeepSeek、智谱 GLM）支持在请求中启用 thinking，并在流式 delta 中分开返回 `reasoning_content` 与 `content`。本仓仅支持这两个 provider，正好可走原生通道，无需文本标签协议。

产品对换行已锁定：**编排阶段** thinking 末尾要 `\n`；**LLM** thinking 增量末尾不要加 `\n`。

## Goals / Non-Goals

**Goals:**

- `thinking_enabled=True` 时真正打开 deepseek / glm（含 zhipu 别名）的原生流式思考
- 稳定映射 `reasoning_content` → `LLMResponse.thinking`，`content` → 正文
- 编排 thinking（`emit_thinking`、路由里的 `llm_start` 等）统一保证末尾 `\n`
- LLM thinking 原样透传，不加尾部 `\n`
- 去掉或降级正文标签解析主路径

**Non-Goals:**

- Intent 同步 `invoke`、Q&A 捷径命中路径的 thinking
- 改 SSE 事件类型或字段名
- 强制提示词 `[思考]` 标签或跨 chunk 文本状态机
- 为不支持 thinking 的第三方模型做通用兼容层（本仓仅 deepseek/glm）
- 改 clinic/tip 业务提示词（闺蜜口吻、字数等）

## Decisions

### 1. 请求侧：按调用开启 thinking，而非永久写进缓存客户端

- **选择**：`stream(..., thinking_enabled=True)` 时，对本次 `astream`（或临时绑定的模型）传入 `extra_body={"thinking": {"type": "enabled"}}`（或 ChatOpenAI 等价的 `model_kwargs` / `extra_body`）。
- **理由**：`_get_client` 按 `provider:model` 缓存；若把 thinking 写进单例客户端，会污染同模型的 `invoke`（意图分析等不应开思考）。
- **备选**：缓存两套客户端（thinking / 非 thinking）——可行但多一倍连接与 key 管理；首版优先调用时覆盖。

### 2. 响应侧：优先读原生 reasoning 字段，废弃标签扫描

- **选择**：`thinking_enabled=True` 时经缓存 `ChatOpenAI.root_async_client` 调 `chat.completions.create(..., extra_body=thinking)`，从 delta 读 `reasoning_content` → `LLMResponse.thinking`，`content` → 正文。同一 chunk 两者可并存。
- **理由**：本仓安装的 `langchain-openai` 明确**不**提取第三方 `reasoning_content`；仅 `astream` + 标签解析无效。底层 OpenAI 客户端能拿到原生字段。
- **备选**：引入 `langchain-deepseek` / 智谱专用包——多依赖；跨 chunk `[思考]` 状态机——补从未打开的伪模式，不做。

### 3. 换行：编排补 `\n`，LLM 不加

| 来源 | 规则 |
|------|------|
| `emit_thinking` / 图节点字幕 | 若 `content` 非空且不以 `\n` 结尾，追加 `\n` |
| 路由 `llm_start` 等编排字幕 | 同上（可走同一小工具函数，或依赖 `emit_thinking` 统一出口） |
| `LLMResponse.thinking` / SSE 转发 LLM 增量 | **不**追加 `\n` |

- **理由**：编排字幕是完整一句，换行便于前端分段；LLM 思考是 token 增量，客户端自行拼接，末尾加 `\n` 会污染流。

### 4. 范围：仅 stream + clinic/tip 已开开关的路径

- Intent invoke、改写、Q&A 等保持现状。
- 不改编排图拓扑；只修客户端映射与 thinking 文案出口。

## Risks / Trade-offs

- **[Risk] 部分 GLM/DeepSeek 模型名不支持 thinking → 请求报错**  
  → Mitigation：仅在 `thinking_enabled` 路径打开；错误打日志并向上抛出（与现有 stream 失败一致）；文档/任务注明需用支持思考的模型。

- **[Risk] LangChain 对 `reasoning_content` 字段位置因版本而异**  
  → Mitigation：单测用假 chunk 覆盖常见属性路径；实现时集中一个小提取函数。

- **[Risk] 缓存客户端若误绑 extra_body 影响 invoke**  
  → Mitigation：决策 1，调用时覆盖，不改共享默认客户端的永久配置。

- **[Trade-off] 去掉标签兜底后，未开原生 thinking 的模型 thinking 恒空**  
  → 可接受：本仓仅 deepseek/glm，且目标就是原生通道。

## Migration Plan

1. 合并后 clinic/tip 流式在支持思考的模型上应出现真正的 thinking SSE（不再几乎只有编排字幕）。
2. 前端无需改字段；若依赖「每条 thinking 必以 `\n` 结尾」，需区分编排 vs LLM（仅编排保证）。
3. 回滚：还原 `llm_client.stream` 与 `emit_thinking` 即可；无数据迁移。

## Open Questions

- 智谱具体模型是否统一用 `thinking.type=enabled` 与 DeepSeek 同形；实现时以当前官方/现网文档为准，若字段名不同则在 provider 分支里适配，对外仍映射到 `LLMResponse.thinking`。
