## Context

客户端：thinking `content` 段首 `\r` 表示清空前置/新开展示。编排字幕已由 `emit_thinking` 段首加 `\r`。LLM reasoning 经 `emit_llm_thinking_delta` / 路由直转，长文追加成一大串。用户拍板：不改编排与旧首包逻辑；仅在流式 LLM 思考上，句界结束后**下一句开头**加 `\r`；句末不贴 `\r`（否则最后一句被清空）。句界：`。！？` 与 `.!?`。范围：全部 agent 的 LLM thinking。

## Goals / Non-Goals

**Goals:**

- 共用 rewriter：输入 reasoning 增量 → 输出可带「下一句首 `\r`」的增量序列。
- 所有 SSE LLM thinking 出口走该 rewriter（`stream_llm_collect` + clinic 等直转路径）。
- 编排 `emit_thinking`、既有「本流/本段首次 LLM 首包 `\r`」保持不变（可叠加）。

**Non-Goals:**

- 不改客户端协议字段。
- 不给每个 token 加 `\r`；不在句界字符后贴 `\r`。
- 不做英文缩写（`e.g.`）精细消歧（可接受误切）。
- 不生成测试文件。

## Decisions

### D1：下一句首加 `\r`，句末不加

状态机：

```
prev_ended = False  # 上一输出是否停在句界
feed(delta):
  for 切出的片段 / 或按字符扫描:
    if 开始输出非空正文且 prev_ended:
      输出 = "\r" + 正文前缀…
      prev_ended = False
    若本段以句界字符结束:
      prev_ended = True
流结束：刷出残余正文；若曾 prev_ended 且无新正文，不再单独发 "\r"
```

**Alternatives：** 句末拼 `\r` — 否决（最后一句清空）。每 delta 加 `\r` — 否决（一字一清）。

### D2：句界字符集

仅：`。！？` 与 `.!?`。跨 chunk 靠缓冲/标志，不要求整句攒齐再发（可边扫边发，仅在「上句已结束后的下一句第一个非空白字符」前置 `\r`）。

### D3：挂载点

1. 新增 `app/shared/graphs/thinking_sentence_cr.py`（或等价）：`ThinkingSentenceCrRewriter`。
2. `stream_llm_collect`：每个 `chunk.thinking` 经 rewriter 再 `on_thinking` / `emit_llm_thinking_delta`；一次 collect 结束 flush。
3. clinic（及任何直转 `chunk.thinking` 的 SSE）：同一 rewriter 实例 per LLM 调用流。
4. 编排路径不经 rewriter。

### D4：与「首包开泡」叠加

若路由仍对「本流首次 LLM」做 `ensure_orchestration_thinking_content`，与句 rewriter 可并存：首包可能已有 `\r`；rewriter 在 `prev_ended` 后再加。幂等：已 `startswith("\r")` 的片段不再重复前置（可选，防双 `\r`）。

## Risks / Trade-offs

- [英文 `.` 误切] → 思考多为中文；接受  
- [漏接某条直转 thinking 路径] → tasks 审计 clinic/care-alert/growth/intent pending  
- [与旧「后续禁止 `\r`」字面冲突] → 本 change 规格收窄为允许句级下一句首  

## Migration Plan

1. 发版 shared rewriter + 全 SSE LLM thinking 出口接线。  
2. 客户端无需改协议。  
3. 回滚：rewriter 改为透传。

## Open Questions

（无：句界、下一句首加 `\r`、全 agent、不改编排已拍板。）
