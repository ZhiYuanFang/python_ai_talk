## 1. 配置

- [x] 1.1 在 settings 增加 `knowledge_min_score`（默认 0.6）、`knowledge_prompt_top_k`（默认 1）；将 `companion_session_max_turns` 默认改为 3

## 2. 知识过滤

- [x] 2.1 在 `search_vectors`（或 shared 过滤函数）按 score 降序取 top-K，丢弃低于 `knowledge_min_score` 的条目，写入 State.`knowledge`
- [x] 2.2 确认 tip/clinic 会话 `knowledge_ids` 取自过滤后的 knowledge（无知识则为空）

## 3. 对话窗

- [x] 3.1 确认 companion session 截断与 `chat_context` 使用更新后的 max_turns=3（含中文注释说明）
