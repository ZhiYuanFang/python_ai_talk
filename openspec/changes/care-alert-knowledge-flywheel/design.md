## Context

`POST /v1/care-alert/analyze` 已走 `search_vectors` → `mother_baby_knowledge`，并在空知识时用 Go `kg_context` 回填；`/feedback` 仅日志 ACK。Python 在 `normalize_care_alert_items` 已为每条 item 生成 `suggestionId`。用户要求：像 clinic 一样做通识飞轮；LLM 用本机史+通识判断是否留意；**准确优先**——无合格向量分知识时不硬塞。

## Goals / Non-Goals

**Goals:**

- 提示词：史提供信号，合格通识校准「是否值得留意」；无合格通识不编造、不硬塞。
- 检索：未过相似度/质量门槛则 knowledge 为空；去掉（或关闭）不合格 `kg_context` 顶替硬塞。
- 映射：`suggestionId → knowledge_ids` 持久化（Redis）。
- feedback：`follow_up`→+1、`ignore`→−1 调通识质量分；仍返回 ok，失败不阻断。

**Non-Goals:**

- 不做自由文本 NLP；不改 ignore|follow_up 枚举。
- 不实现跳过 LLM 的「加速捷径」（飞轮目标是更准，不是秒回）。
- 不新建独立护理知识 Collection；继续 `mother_baby_knowledge`。
- 不强制 Flutter/Go 改请求体（映射在 Python 侧用已有 suggestionId）。

## Decisions

### D1: 「映射」= suggestionId 到通识文档 id 的查找表

本轮 analyze 进 prompt 的 `knowledge` 经 `extract_knowledge_ids` 得到列表；对该批产出的每个 `suggestionId` 写入同一组 ids（一批检索服务多条留意项）。

```
key: care_alert:flywheel:{suggestion_id}
value: {"device_no","day","knowledge_ids":[...]}
TTL: 与日缓存同量级（建议 7 天，可配置）
```

feedback 用 `suggestion_id` get → 对每个 id 调 `update_quality_score`。

**Alternatives:** 响应带回 knowledgeIds 让 Go 回传 — 跨仓改动大，本阶段不做。

### D2: 准确优先，禁止硬塞

- 继续 `search_vectors` 的 `knowledge_min_score` / `knowledge_quality_min` / top_k。
- **移除或默认关闭** analyze 末尾「knowledge 空则用 kg_context 填入」的行为；编排侧原文最多作独立「非通识检索」备注且提示词标明不可当作已命中知识（推荐：**直接不再填入 knowledge**）。
- 提示词写明：无「相关知识摘录」时不得假装有通识依据；史信号不足则 items 可为 []。

### D3: intent → feedback 数值

| intent | feedback | 含义 |
|--------|----------|------|
| follow_up | +1 | 愿意追问，通识/提醒有用 |
| ignore | -1 | 忽略，倾向噪音 |

无 mapping 或 ids 空：只打日志 + ok=true。

### D4: 提示词结构

系统提示增加：判定须同时考虑近史与（若有）合格通识；通识用于校准是否「同月龄值得提」，不得写成对方记录；无通识时宁缺毋滥。

## Risks / Trade-offs

- [knowledge 经常为空 → 飞轮少触发] → Mitigation：接受准确优先；可后续优化 query，不降低门槛硬塞。
- [ignore 误伤好知识] → Mitigation：仅对有 mapping 的 ids 扣分；与 clinic 同一降权幅度。
- [Go 覆盖 suggestionId] → Mitigation：若 Go 改写 id，Python 映射失效；CONTRACT 注明以 Python 返回的 suggestionId 为准调用 feedback，或后续支持 register 接口。本设计假设 Go 透传 Python 的 id。

## Migration Plan

1. 部署后新 analyze 开始写 Redis 映射；旧 suggestion 无映射则 feedback 仍 ACK。
2. 回滚：feedback 捕获异常仍返回 ok；可开关跳过质量更新。

## Open Questions

- Go 是否改写 Python 下发的 `suggestionId`？（若会，需在 CONTRACT/Go 侧固定透传。）
