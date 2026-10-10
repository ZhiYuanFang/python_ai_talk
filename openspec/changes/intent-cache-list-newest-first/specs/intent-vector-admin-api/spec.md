## ADDED Requirements

### Requirement: 管理列表按 created_at 新到旧分页
系统 SHALL 在管理端列出 `feeding_intents` 时，先按条目 metadata 的 `created_at` **降序**（新→旧）排列全部条目，再应用请求的 `offset`/`limit` 分页。响应中的 `items` 顺序 MUST 与该排序一致。缺失或空字符串的 `created_at` MUST 排在所有具备非空 `created_at` 的条目之后。`created_at` 相同（或同为空）时 MUST 以稳定次序（如 id 字典序升序）打破平局。本要求 MUST NOT 改变运行时意图匹配、整理重复保留规则，或 bulk/delete 语义。

#### Scenario: 首页先出现较新写入
- **WHEN** 库中存在两条条目，其 `created_at` 分别为较早与较晚的 ISO 时间，且管理方请求 `offset=0` 的列表
- **THEN** 响应 `items` 中较晚 `created_at` 的条目 SHALL 排在较前 `created_at` 的条目之前

#### Scenario: 分页在全局时间序上切片
- **WHEN** 库中条数大于 `limit`，管理方先请求 `offset=0` 再请求下一页
- **THEN** 两页拼接后的顺序 SHALL 等同于按 `created_at` 降序的全局顺序（中间无乱序插入）

#### Scenario: 空 created_at 沉底
- **WHEN** 库中同时存在带非空 `created_at` 与空 `created_at` 的条目
- **THEN** 带非空 `created_at` 的条目 SHALL 全部排在空 `created_at` 条目之前
