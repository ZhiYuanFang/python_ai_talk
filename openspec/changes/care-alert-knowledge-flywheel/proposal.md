## Why

护理留意 `analyze` 虽已检索通识库 `mother_baby_knowledge`，但提示词把知识当弱参考，且 `/feedback` 仅 ACK，未像 clinic 那样把用户 ignore/follow_up 写回通识质量分。缺少「本轮用了哪些知识文档」的记录时，无法对症加减分。同时须坚持准确优先：向量分/质量分未达标时不得硬塞知识进判定。

## What Changes

- **提示词强化**：LLM 须结合本机近史（事实信号）与合格通识（校准是否值得留意）判定；无合格知识时允许仅凭史谨慎判断或少出/不出 items，**禁止**编造通识或为凑列表硬塞知识块。
- **准确优先检索**：沿用（或明确）相似度/质量门槛；未达标则 `knowledge` 为空进入生成；**不得**用未过门槛的编排侧 `kg_context` 顶替为「已检索通识」硬塞进判定（除非未来契约另有合格标记）。
- **映射（suggestion → knowledge_ids）**：analyze 产出每条 item 的 `suggestionId`（Python 已可生成）时，持久化该 id 与本轮进 prompt 的通识文档 id 列表；feedback 凭 `suggestion_id` 取回 ids 再飞轮。
- **真飞轮**：`ignore` → 通识质量下调；`follow_up` → 上调；复用 `vector_store.update_quality_score`（与 clinic 同库）。无 ids 时仍 ACK、不报错。
- 更新 `llm-care-alert-daily/CONTRACT.md` 中「仅 ACK、不 invent 质量分」的过时表述（本变更取代该桩行为）。

### 「映射」指什么（给评审）

不是 NLP 语义映射，而是：

```
analyze 时：suggestionId ──记下──▶ [knowledge_doc_id_1, ...]
feedback 时：suggestion_id ──找回──▶ 对这些 doc 做 +/- 质量分
```

没有这张表，feedback 不知道该改通识库里的哪几条。

## Capabilities

### New Capabilities

- `care-alert-knowledge-flywheel`: 护理留意通识接地判定、suggestion→knowledge_ids 映射存储、固定意图反馈驱动通识质量飞轮；准确优先不硬塞低分知识。

### Modified Capabilities

- `knowledge-flywheel`: 通识质量分更新入口扩展为护理留意 feedback 亦可调用（行为与 clinic 👍/👎 等价：follow_up≈+，ignore≈−）。

## Impact

- 代码：`app/care_alert/**`（prompts、analyze、feedback 路由）、Redis 映射存储（可新建 `care_alert` 下小模块或复用 redis_gate）、`app/shared/vector_store.py`（复用既有 API）。
- API：`POST /v1/care-alert/feedback` 从空 ACK 变为可副作用更新质量分；请求体字段不变（非 BREAKING）。analyze 响应字段不变（suggestionId 已有）。
- 跨仓：Go/Flutter 可继续 best-effort 调 feedback；无需立刻改契约字段。建议同步 CONTRACT 说明飞轮已生效。
