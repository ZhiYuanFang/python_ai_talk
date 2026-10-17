## Why

意图一次请求会串多次 LLM，每次都先生成整段 reasoning 再写正文，客户端看到的思考字幕又难以阅读。意图侧不再需要模型的具体思考过程，关掉它可以缩短反应时间；等待期间用两条固定字幕轮换，让用户知道还在处理。

## What Changes

- 喂养意图链路上的 `stream_llm_collect` 调用 `thinking_enabled=False`。
- 通义千问在关闭思考时请求体带 `enable_thinking: false`，避免默认仍先思考。
- 这些调用等待期间，对外 thinking 从调用开始起每 1 秒轮换 `\r努力思考中` 与 `\r正在思考中`，模型 reasoning 不推给客户端。
- 轮换在该次调用结束时停止。图节点固定编排字幕保持原样。
- 诊所回答、诊所的翻记录判定、成长轨迹、留意点仍 `thinking_enabled=True`，仍透出模型 reasoning。
- **BREAKING**（约定）：`openspec/project.md` 里「对外 SSE 每次 LLM 必须开启 thinking 并透出 reasoning」对意图链路改为例外。

## Capabilities

### New Capabilities

- `intent-llm-thinking-off`: 意图链路关闭模型思考，并用两条固定字幕按秒轮换表示正在处理

### Modified Capabilities

- （无）当前基线 `openspec/specs/v0.0.1.md` 未单独描述意图 LLM 的 thinking 开关。工程约定写在 `openspec/project.md`，实现时同步改该段，不另立基线能力目录。

## Impact

- 喂养模块里所有 `stream_llm_collect` 调用点（分类、切段、维度判定、备注、事件反查、播报策略、预测回答、澄清、漏答、日汇总）。
- `app/shared/llm_client.py` 关闭思考时的通义请求体。
- `app/shared/graphs/stream_llm_collect.py` 在 `thinking_enabled=False` 时发轮换字幕，不再转发 reasoning。
- `openspec/project.md` 与 `AGENTS.md` 中对应的 SSE thinking 约定。
- 诊所 `stream_response`、成长轨迹、留意点、共享判定节点不改。
