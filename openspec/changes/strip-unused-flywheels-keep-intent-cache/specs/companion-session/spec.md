## ADDED Requirements

### Requirement: Companion session without knowledge or QA flywheel metadata

陪伴会话仍可以 `device_no` 共享 tip/clinic 近轮对话。系统 MUST NOT 要求 `last_suggestion` 携带 `knowledge_ids`、`qa_match_id` 或为通识/Q&A 飞轮服务的判定字段；MUST NOT 因缺少这些字段而失败。

#### Scenario: Tip and clinic still share turns

- **WHEN** 同一 `device_no` 先 tip 后 clinic
- **THEN** clinic 仍可读取近期对话轮次

#### Scenario: No flywheel fields required on append

- **WHEN** tip 或 clinic 成功追加一轮助手回答
- **THEN** 系统 MUST NOT 依赖写入 `knowledge_ids` / `qa_match_id` 才能完成会话持久化

## REMOVED Requirements

### Requirement: Tip opening writes a full turn
**Reason**: 原要求含「更新待判定建议元数据（含 knowledge_ids）」；由上方 ADDED 取代为无飞轮字段义务。
**Migration**: tip 仍追加合成 user + assistant 文本轮次即可。
