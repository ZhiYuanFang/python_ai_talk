## 1. 格式化与提示词

- [x] 1.1 实现今昨过滤 + 紧凑行 + eventName=eventId 对照表（中文注释）
- [x] 1.2 `care_alert_analyze` 用紧凑块替换 JSON slim；系统提示说明按对照表回填 eventId
- [x] 1.3 analyze 拉取改为近两日（last_2_days）；fetch_history 支持该 time_range

## 2. 通识与 clinic 同配置

- [x] 2.1 不设 care_alert `knowledge_prompt_top_k` 覆盖；走全局默认（1）
- [x] 2.2 提示词 `_compact_knowledge` limit=1

## 3. 校验

- [x] 3.1 `openspec validate care-alert-compact-history --strict` 通过
