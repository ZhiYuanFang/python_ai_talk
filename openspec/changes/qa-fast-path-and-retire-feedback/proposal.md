## Why

Clinic 已能通过隐式采纳更新知识块 `quality_score`，但检索仍只看相似度，优质答案无法复用；显式 `/feedback` 与产品主路径（多轮隐式采纳）重复且 `answer_id` 常对不上 chunk。需要把「被采纳的高质量问答」沉淀为可检索捷径，并在命中时跳过完整诊疗准备图，同时下线死路径显式反馈。

## What Changes

- 新增全局 **Q&A 捷径库**（向量检索）：以 LLM 改写后的独立问句为 query key；写入侧与检索侧使用同一改写规则；仅在隐式 `accepted` 且本轮改写成功时入库。
- Clinic 图在隐式飞轮之后增加捷径路径：取 profile → 生日换算月龄 → 改写问句 → 检索 Q&A；当 **相似度 > 0.8**、**质量达标**、**月龄带匹配** 时直接返回答案并 END，否则走现有 prepare（含 needs-history 等）。
- 改写失败/超时 → 本轮 **miss**（不以原文 query 回退检索 Q&A）；未知宝宝年龄 → 不命中捷径。
- 月龄带：`<36 个月` 按月（`m{N}`）；`≥36 个月` 按年（`y{Y}`）；月龄计算复用 tip 的 `derive_baby_age` 思路，并让 clinic 提示词注入月龄而非原始生日。
- 通识知识检索增加 `quality_score` **硬过滤**（默认阈值 0.7）。
- 历史点查 / `force_needs_history` / 敏感医疗类问题不走捷径（设计中明确拦截规则）。
- **BREAKING**：删除 Python `POST /v1/clinic/feedback` 与 `POST /v1/tip/feedback`；文档与相关 schema 清理。Go/Flutter 侧若仍调用将得到 404，需跨仓协调下线或忽略。

## Capabilities

### New Capabilities

- `qa-fast-path`: 问句改写、全局 Q&A 向量库、月龄带匹配、命中后直接回答并跳过完整 clinic 准备链路。
- `knowledge-quality-hard-filter`: 通识（及必要时 tip）知识检索按 `quality_score` 硬过滤。
- `baby-age-months-context`: 生日→月龄共享推导，clinic 提示与飞轮统一用月龄/月龄带。

### Modified Capabilities

- `retire-explicit-feedback`: 移除 clinic/tip 显式 feedback API 与兼容说明；知识飞轮仅依赖隐式采纳。

## Impact

- **图**：`clinic_graph`（飞轮后捷径子链）、可能共享节点（rewrite / search_qa / derive_age）。
- **存储**：新 Q&A collection（或等价命名空间）+ metadata：`age_band`、`quality_score`、`standalone_question`、`answer` 等。
- **检索**：`vector_store` / knowledge 查询增加 quality 过滤；QA 检索独立路径。
- **API**：**BREAKING** 删除 `/v1/clinic/feedback`、`/v1/tip/feedback`；`FeedbackRequest` 与 docs 中显式反馈描述。
- **跨仓**：Go `ClinicFeedback`/`TipFeedback`、Flutter 👍/👎 若仍存在需同步移除或改为 no-op；本 change 以 Python 仓为准并在 design 中标注协调点。
- **依赖**：已有隐式采纳、`knowledge_ids` 质量更新、LangGraph 统一编排与 progressive thinking。
