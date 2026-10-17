## Context

LLM reasoning 经 `stream_llm_collect` → `ThinkingSentenceCrRewriter` → `emit_llm_thinking_delta` / `on_thinking` 推到 SSE。提示词已要求思考用中文，模型仍会写出字段名、JSON 与 markdown。回答正文走 `chunk.content`，不经该改写器。图节点固定中文字幕走 `emit_thinking`，也不经该改写器。

## Goals / Non-Goals

**Goals:**

- 在共用管道里，对即将展示的 reasoning 增量去掉英文字母与常见格式符号。
- 所有走 `stream_llm_collect` 的思考字幕一并生效，不按智能体分支。
- 保留中文、数字、空白、中文句界，以及客户端需要的段首 `\r`。

**Non-Goals:**

- 不改提示词、不改模型输出约束。
- 不改回答正文，不改编排字幕。
- 不要求过滤后句子仍通顺或可复述。
- 不新增按模块开关。

## Decisions

### D1：挂在句界改写器入口

在 `ThinkingSentenceCrRewriter.feed` 吃入增量后、按句拆分前先剔除字符。所有 `stream_llm_collect` 调用自然生效。备选是在路由层过滤，会漏掉其它图与 pending 回调。

### D2：按字符删除，直接丢掉

去掉 `A–Z` / `a–z`，以及常见 JSON / markdown 符号：`{}[]"'`\`:#*_`\` 与反引号。数字、中文标点、空白、`.!?`（句界仍认）与 `\r` 保留。不换成空格以外的占位符，避免字幕里多出空洞噪声；连续空白可压成一个，也可不压，以实现简洁为准。

### D3：整段被剔空则不透出

过滤后若该片段只剩空白或为空，本条不推 SSE，避免空气泡。

### D4：不碰正文与编排字幕

`chunk.content` 与 `emit_thinking` 路径保持原样。

## Risks / Trade-offs

- [中英混写专有名被拆掉] → 接受。思考流不要求可读完整。
- [句界依赖英文 `.` `!` `?`] → 这些符号本身是句界，保留；字母仍删。
- [全英思考片段变成空] → 不推该片段，字幕少闪几下即可。

## Migration Plan

发布后立即生效。回滚是去掉改写器里的剔除步骤。

## Open Questions

无。
