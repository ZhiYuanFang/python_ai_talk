## 1. 共用 rewriter

- [x] 1.1 实现 `ThinkingSentenceCrRewriter`（句界 `。！？.!?`；上句结束后下一句首加 `\r`；句末不贴 `\r`；flush 不发裸 `\r`）
- [x] 1.2 中文注释说明与客户端「段首 `\r` 清空」语义

## 2. 接线全 agent LLM thinking

- [x] 2.1 `stream_llm_collect`：thinking 增量经 rewriter 再透出；每次调用结束 flush
- [x] 2.2 clinic 主答等直转 `chunk.thinking` 的 SSE 走同一 rewriter
- [x] 2.3 审计 care-alert / growth-trajectory / intent pending：凡 LLM thinking 出口均接线；编排 `emit_thinking` 不改

## 3. 验收

- [ ] 3.1 手工：多句 reasoning → 第二句起内容带段首 `\r`，界面短文案轮换
- [ ] 3.2 手工：以句号结束且无下文 → 最后一句仍显示，不被清空
- [ ] 3.3 手工：编排字幕仍逐步 `\r` 开泡，行为与改前一致
