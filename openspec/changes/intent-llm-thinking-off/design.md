## Context

喂养意图的 LLM 都经 `stream_llm_collect`，默认 `thinking_enabled=True`。`llm_client.stream` 在开启时附带 `{"thinking": {"type": "enabled"}}`（DeepSeek / 智谱写法），并先流出 reasoning。现网强制型号是通义 `qwen3.7-flash`。关闭分支只是改走 LangChain `astream` 且不带该字段，通义千问 3 默认仍可能先思考。

诊所回答走 `stream_response`，自己把 reasoning 经 `ThinkingSentenceCrRewriter` 推出去。成长轨迹、留意点、诊所的两个共享判定也走 `stream_llm_collect` 且保持开启。

客户端约定：thinking 的 content 以 `\r` 开头则清掉上一句。

## Goals / Non-Goals

**Goals:**

- 意图链路不再让模型生成思考，缩短每次调用的首字与总时间。
- 通义在关闭时显式 `enable_thinking: false`。
- 这些调用从开始到结束，对外 thinking 每 1 秒轮换两条固定字幕。
- 图节点固定编排字幕保持原样。

**Non-Goals:**

- 不改诊所回答、诊所翻记录判定、成长轨迹、留意点的 thinking 开关与 reasoning 透出。
- 不删 `ThinkingSentenceCrRewriter`；`thinking_enabled=True` 的路径继续用它。
- 不把轮换文案做成可配置。
- 不改回答正文的聚合方式。

## Decisions

1. **只在喂养调用点传 `thinking_enabled=False`。** `stream_llm_collect` 默认仍为 `True`。新的诊所或成长调用不会被默认关掉。喂养侧调用点：`classify_intent`、`resolve_segments`、`speak_predict`、`segment_dim_llm`、`segment_remark`、`history_event_guess`、`clarification`、`history_speak_policy`、`agent_miss_soft_reply`、`history_daily_context`、`dim_resolve`。

2. **通义关闭必须写进请求体。** `thinking_enabled=False` 且 provider 为 `aliyun_dashscope` 时，请求带 `enable_thinking: false`。LangChain `astream` 若带不上该字段，关闭分支改用与开启分支相同的底层客户端，只换 extra_body。其他厂商的关闭分支维持现在的「不带 thinking extra_body」。

3. **轮换挂在 `stream_llm_collect` 的关闭分支。** 调用一开始就推 `\r努力思考中`，之后每 1 秒在它和 `\r正在思考中` 之间切换。`\r` 后不加空格。用独立异步任务，不堵住正文流；`finally` 里取消任务。模型 reasoning 不转发。`on_thinking` 与 `emit_llm_thinking_delta` 只收到这两句。

4. **一次调用一条计时器。** 意图图是顺序的，后一次调用的 `\r` 会盖住前一次。节点固定字幕仍由 `emit_thinking` 发出；LLM 一开始，轮换句会盖住它，调用结束后下一句编排字幕再盖回来。

5. **工程约定同步改文案。** `openspec/project.md` 与 `AGENTS.md` 写明：意图链路的 SSE LLM 使用 `stream(thinking_enabled=False)`，对外 thinking 是这两句轮换；其余对外 SSE LLM 仍开启 thinking 并透出 reasoning。

## Risks / Trade-offs

- [关掉思考后分类、维度判定少了一段推理，边界句子可能更不稳定] → 接受；用户要的是反应速度。提示词仍要求中文 JSON 正文。
- [通义未显式关闭时仍然先思考，开关形同虚设] → 关闭分支必须带 `enable_thinking: false`。
- [轮换在短调用上只来得及打出第一句] → 第一句在调用开始时立刻发送，1 秒内结束的调用也有一条「努力思考中」。
- [诊所仍展示模型思考原文] → 本变更范围只到意图链路。

## Migration Plan

- 先改 `llm_client` 的关闭请求体，再改 `stream_llm_collect` 的轮换，最后给喂养调用点传 `False`，并改两处约定文案。
- 回滚：调用点改回默认 `True`，去掉轮换任务与通义关闭字段。

## Open Questions

- （无）
