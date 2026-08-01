## Context

`search_vectors` 固定 `n_results=5` 且无分数门槛，clinic/tip/suggest 提示词把全部 `knowledge` 全文写入「可参考的知识」。陪伴会话默认最多 5 轮写入 Redis 并注入 `chat_context`。日志显示知识块偏大，需收紧。喂养 `history_events` 本轮不改。

## Goals / Non-Goals

**Goals:**

- 进 LLM 的知识最多 1 条，且 `score >= 0.6`；否则空列表
- 陪伴对话最多 3 轮（存储截断与 prompt 一致）
- 飞轮 knowledge_ids 与注入 prompt 的知识一致
- 门槛/K/轮次可配置

**Non-Goals:**

- 不改喂养历史条数
- 不改向量库切块策略
- 不改 HTTP 契约
- 不重训/重嵌知识库

## Decisions

### 1. 过滤落点：检索节点产出即过滤

- **选择**：在 `search_vectors`（或紧随其后的共享 `filter_knowledge_for_prompt`）将 State.`knowledge` 收成 0～1 条
- **理由**：clinic/tip/intent 共用该节点，一处生效；提示词无需再滤
- **备选**：仅在 prompt 构建时滤（State 仍持 5 条，飞轮易误用弱文档）

### 2. 检索仍可多取再筛

- **选择**：底层 `n_results` 可仍为较小值（如 3～5），再按 score 排序取 top-1 并过门槛 T=0.6
- **理由**：给排序留余地；最终进 State/prompt 仍最多 1 条

### 3. 默认配置

| 配置 | 默认 | 含义 |
|------|------|------|
| `knowledge_min_score` | 0.6 | 低于则不注入 |
| `knowledge_prompt_top_k` | 1 | 最多注入条数 |
| `companion_session_max_turns` | 3 | 原 5 |

### 4. 对话窗

- **选择**：只改默认 `companion_session_max_turns=3`；`format_chat_turns_for_prompt` 读会话 turns（已被截断）
- **理由**：存储与注入一致，无需第二套「prompt 只取 3」逻辑

### 5. 飞轮 ids

- **选择**：`extract_knowledge_ids(final_state["knowledge"])` 在过滤后执行（路由已如此）
- **理由**：无知识则不记 ids，避免弱文档飞轮

## Risks / Trade-offs

- [T=0.6 过严导致几乎无知识] → 配置可调；陪伴人格允许无知识
- [score 刻度与距离换算敏感] → 沿用现有 `1/(1+distance)`；用日志观察 top1 score
- [已有 Redis 会话仍可能含 5 轮] → 下次 `save`/`append_turn` 会按新 max 截断

## Migration Plan

1. 部署新默认配置
2. 观察 tip/clinic 日志中知识条数与 score
3. 回滚：调低 T 或调回 top_k/max_turns

## Open Questions

- 无（T=0.6、K=1、对话 3 轮已由产品确认）
