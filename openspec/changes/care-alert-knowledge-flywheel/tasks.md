## 1. 准确优先与提示词

- [x] 1.1 强化 `care_alert_analyze` 提示词：史给信号 + 合格通识校准是否留意；无通识不编造、宁缺毋滥
- [x] 1.2 去掉（或关闭）analyze 用 `kg_context` 填入空 `knowledge` 的硬塞逻辑；保留 search_vectors 门槛行为
- [x] 1.3 更新 `llm-care-alert-daily/CONTRACT.md`：feedback 真飞轮 + 不硬塞不合格知识

## 2. 映射存储

- [x] 2.1 新增 Redis 映射读写（`suggestion_id → knowledge_ids`，TTL 默认 7 天，中文注释）
- [x] 2.2 analyze 成功产出 items 后，对本轮 `extract_knowledge_ids(knowledge)` 为每个 suggestionId 写入映射

## 3. Feedback 飞轮

- [x] 3.1 `care_alert_feedback`：按 intent 取映射并对 ids 调用 `update_quality_score`（follow_up=+1，ignore=-1）
- [x] 3.2 无映射/更新失败时打日志仍返回 ok=true

## 4. 校验

- [x] 4.1 `openspec validate care-alert-knowledge-flywheel --strict` 通过
