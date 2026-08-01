## Why

tip/clinic 把向量检索 top-5 全文塞进「可参考的知识」，弱匹配也进 prompt，token 偏高。陪伴会话默认保留 5 轮对话，续聊上下文同样偏长。需要在不改喂养记录逻辑的前提下，只注入高匹配知识，并缩短对话窗。

## What Changes

- 知识注入：检索后仅保留 **最高分 1 条（K=1）**；相似度低于 **0.6** 时不注入任何知识（宁可口语陪聊）
- 相似度门槛与检索条数可配置，默认阈值 **T=0.6**
- 陪伴对话窗：`companion_session_max_turns` 默认 **5 → 3**（Redis 截断与 prompt 中 `chat_context` 一致）
- 隐式飞轮的 `knowledge_ids` 与 **实际注入 prompt 的知识** 对齐（无注入则空）
- **不**修改喂养 `history_events` 条数逻辑；**不**改 HTTP 路径

## Capabilities

### New Capabilities

- `companion-context-budget`: 陪伴链路 LLM 上下文预算（知识 top-1 + 分数门槛、对话最多 3 轮）

### Modified Capabilities

- （无：`openspec/specs/` 下无已归档基线；会话窗数值调整在本 change 的新 capability 中规定）

## Impact

- **代码**：`app/shared/graphs/nodes/search_vectors.py`（或共享过滤函数）；`app/config/settings.py`；`app/shared/companion_session.py` 默认轮次；tip/clinic 写会话与 `extract_knowledge_ids` 使用过滤后列表
- **API**：无契约字段变更；响应内容可能因知识更少而更口语
- **配置**：新增/调整 `knowledge_min_score`（默认 0.6）、`knowledge_prompt_top_k`（默认 1）、`companion_session_max_turns`（默认 3）
