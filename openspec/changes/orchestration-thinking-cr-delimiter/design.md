## Context

编排阶段 thinking 字幕经 `ensure_orchestration_thinking_content` 在非空时强制尾部分隔符，供客户端把多条 SSE thinking 拼 buffer 后切成「条目」。基线当前使用 LF (`\n`)。LLM 流式 `thinking` 增量不经该 helper，可含正文换行。客户端将同步改为按 CR (`\r`) 分割；本变更只改服务端编排字幕尾部分隔符。

## Goals / Non-Goals

**Goals:**

- 编排字幕非空时以单个 `\r` 结尾（幂等：已以 `\r` 结尾则不再追加）。
- 单一 helper 覆盖 `emit_thinking` 与 clinic/tip 路由层 `llm_start` 等字幕。
- Spec 与实现一致；LLM 增量路径保持「不追加条目分隔符」。

**Non-Goals:**

- 不改 LLM 流式 thinking 映射或 SSE 转发逻辑。
- 不在本仓改 Flutter/Go 客户端（由对端同步）。
- 不引入双分隔符兼容期（不剥离旧尾部 `\n`，也不同时认 `\n`/`\r`）。

## Decisions

1. **条目分隔符 = `\r`**  
   - 相对 `\n`：极少出现在中文/模型推理正文，避免与行内换行冲突。  
   - 替代方案：专用 JSON 字段 `item_boundary` / 每条独立 SSE 类型——改动面大，本次不采用。

2. **幂等只认 `\r`（方案 A）**  
   - `endswith("\r")` 则不追加；否则追加 `\r`（即使已以 `\n` 结尾，得到 `…\n\r`）。  
   - 不 `rstrip("\n")`。理由：实现最简；客户端 `split('\r')` 后条目内残留尾部 `\n` 通常无害。  
   - 曾考虑方案 B（先剥 `\n` 再保证 `\r`）：更干净，但非本次选择。

3. **LLM 路径不动**  
   - 继续禁止对 LLM thinking 增量「仅为格式化」追加尾部分隔符（含 `\r`）。  
   - 条目边界仅由编排字幕的尾部 `\r` 提供。

## Risks / Trade-offs

- **[BREAKING]** 旧客户端仍 `split('\n')` → 多条编排字幕可能粘连 → 缓解：与客户端同发/约定切换窗口。  
- **[脏尾部]** 方案 A 下偶发 `…\n\r` → 缓解：客户端 trim 条目或忽略展示用尾空白。  
- **[误用 helper]** 若有人把 LLM 增量也喂给 `ensure_orchestration_thinking_content` → 缓解：注释与 spec 明确禁止；代码审查守住调用点。

## Migration Plan

1. 合并服务端变更与客户端 `split('\r')` 同版本发布。  
2. 回滚：恢复 helper 追加 `\n` 并回滚客户端分割符。

## Open Questions

（无；方案 A 与 LLM 不动已在 explore 中确认。）
