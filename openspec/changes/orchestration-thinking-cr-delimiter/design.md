## Context

客户端协议：thinking 内容若以 `\r` 开头则开新气泡，否则追加到当前气泡。编排字幕与 LLM 推理需各自成泡；`llm_start` 字幕与模型思考正文应为两条气泡。helper 与路由层共同保证段首 `\r`。

## Goals / Non-Goals

**Goals:**

- 编排字幕非空时以 `\r` **开头**（幂等：已 `startswith("\r")` 则不再前置）。
- 同一流式会话中，**第一次**非空 LLM thinking 增量同样保证段首 `\r`；之后的 thinking 增量不加。
- 单一 helper 供编排与「LLM 首包」复用。

**Non-Goals:**

- 不给每个 LLM thinking delta 加 `\r`。
- 不在本仓改客户端。
- 不生成测试文件。

## Decisions

1. **段首 `\r`（开泡符）**  
   - 替代尾部 `\r`：与客户端「段首 = 新气泡」一致。  
   - 幂等：`startswith("\r")`。

2. **LLM 仅首包加 `\r`**  
   - 否则会粘在 `llm_start` 字幕气泡上。  
   - 路由层用布尔标志 `first_llm_thinking`；首包走 helper，其后原样。

3. **Q&A 捷径**  
   - 无 LLM thinking 流则不额外发 `\r`。

## Risks / Trade-offs

- **[BREAKING]** 仍按尾部 `\r` 或 `split` 的旧客户端会错切 → 与客户端同发。  
- **[无 thinking]** 模型不吐 reasoning 时只有字幕泡，无独立 LLM 泡 → 可接受。

## Migration Plan

1. 服务端与客户端「段首 `\r`」同版本发布。  
2. 回滚：恢复旧 helper/路由逻辑。

## Open Questions

（无。）
