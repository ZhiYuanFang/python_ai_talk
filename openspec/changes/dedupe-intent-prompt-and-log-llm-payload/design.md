## Context

意图分类通过 `build_intent_classification_system_prompt(event_dictionary)` 注入完整 `{id,name}` 目录，又通过 `build_intent_classification_user_message(text, event_dictionary)` 再拼事件名列表。审计其它 prompts 后确认：仅此处存在 system+user 同类重复；`data_requirement` 等为「规则在 system、目录/上下文在 user」，属健康分工。

`llm_client.invoke`/`stream` 目前仅记录 provider/model，开发者无法从日志核对实际发给模型的内容。已选定 **INFO 全量**打印策略。

约束：不改事件字典 24h 刷新与喂养数据飞轮。

## Goals / Non-Goals

**Goals:**

- 意图 user 消息去重，只保留用户输入与简短分析指令
- 在 LLM 客户端统一 INFO 打印完整 system_prompt 与 messages
- 将「其它 prompt 无重复」固化为 design 记录，避免误改

**Non-Goals:**

- 不把意图目录从 system 挪到 user（与 data_requirement 风格统一留给后续）
- 不改其它 prompt 文件
- 不做日志截断、DEBUG 切换或配置开关（本次按 INFO 全量）
- 不改 `event_cache` / `event_vector_store` / 飞轮

## Decisions

### 1. 事件目录仅留在 system

- **选择**：删除 user 中的「可用事件类型」行；`build_intent_classification_user_message(text)` 不再接收 `event_dictionary`
- **理由**：system 已有 id+name；user 侧名字列表无增量且缺 id
- **替代**：user 放带 id 的短目录、system 只留规则 —— 超出「删重复」范围

### 2. 其它 prompt 只审计不改

- **选择**：design 记录审计表，代码不动
- **理由**：无同类重复；改动增加回归面

### 3. INFO 全量日志落在 llm_client

- **选择**：`invoke` 与 `stream` 在调用模型前各打一次 INFO，内容含 provider、model、system_prompt 全文、每条 message 的 role+content
- **理由**：所有调用方自动覆盖；用户明确选择 A：INFO 全量
- **替代**：各节点自行打日志 —— 易漏；DEBUG/截断 —— 用户已否决本次采用

## Risks / Trade-offs

- [生产日志暴涨 / 含用户原文与事件字典] → 接受为调试优先；后续可加开关另开 change
- [去重后个别模型 event_id 命中变差] → 回归意图分类；必要时再评估「近因目录」
- [多行 INFO 刷屏] → 可用分隔标记（如 `--- LLM request payload ---`）便于检索

## Migration Plan

1. 部署后观察意图分类与其它 LLM 路径日志是否出现完整 payload
2. 抽检意图请求：user 消息不再含事件名 JSON 数组
3. 回滚：还原三处文件即可

## Open Questions

- 无。
