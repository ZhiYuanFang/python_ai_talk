## ADDED Requirements

### Requirement: 已确认原话缓存为整份 CRUD 意图
系统 SHALL 在用户确认（或意图缓存高置信命中后直接执行）且批量落库至少一条成功后，将 **改写后的独立问答句**（不得是「嗯/是的」等续聊词）写入独立意图缓存（不得作为已拆除的 `feeding_events` 单事件表达）。缓存载荷 MUST 包含操作 `op`（`create|read|update|delete`）及 `events` 列表（可多件）；查记录可含 `remark_keyword`。系统 MUST NOT 将具体历史记录主键 `history_id` 作为改/删缓存的可复用字段写入。未确认或零条成功 MUST NOT 写缓存。

#### Scenario: 多事件确认后整句可再次命中
- **WHEN** 用户输入「吃完奶，换了尿布」并确认 `create` 且 `events` 含喝奶与换尿布两件叶子
- **AND** 落库成功
- **THEN** 系统 SHALL 将改写后的独立句与整份 `{op: create, events: [...]}` 写入意图缓存
- **AND** SHALL NOT 把该整句仅关联到其中一个 `event_id`
- **AND** SHALL NOT 缓存本轮 `history_id`

#### Scenario: 改删缓存不含记录主键
- **WHEN** 用户确认「把刚才喝奶改成 150」且执行成功
- **THEN** 写入缓存的载荷 MUST NOT 依赖本轮解析出的 `history_id` 作为下次直接执行目标
- **AND** 下次命中后系统 MUST 重新查询最近记录再执行

### Requirement: 意图缓存是意图路径唯一向量匹配
当意图缓存相似度达到实现所定高置信阈值时，系统 SHALL 采用缓存中的 `op` 与 `events` 作为意图结果。系统 MUST NOT 再查询 `feeding_events` 或任何事件名向量以覆盖该结果。缓存未命中时 SHALL 进入分类（可先备注探针），SHALL NOT 降级到事件名 Top-1。

#### Scenario: 缓存命中跳过分类
- **WHEN** 用户再次输入与已缓存多事件原话高度相似的句子
- **THEN** 系统 SHALL 复述缓存的多事件 `create` 结果进入执行层
- **AND** SHALL NOT 再检索事件名向量

### Requirement: 改删命中后必须现查再执行
意图缓存命中 `op` 为 `update` 或 `delete` 时，系统 MUST 先按事件向兄弟仓查询当前应操作的历史行，再调用更新或删除接口。查询失败或找不到行时 MUST NOT 写库，MUST 在 `content` 中说明。

#### Scenario: 删除命中但无记录
- **WHEN** 缓存命中 `delete` 某事件
- **AND** latest/filter 返回空
- **THEN** 系统 SHALL NOT 调用删除 HTTP
- **AND** `content` SHALL 说明未找到可删记录

### Requirement: 查记录缓存带备注关键词不带事件假名
当查记录因备注探针确认并成功播报后写入缓存时，载荷 MUST 使用字典 `event_ids` 与 `remark_keyword`，MUST NOT 把用户口中的专名（如 AD）写成 `event_id` 或新事件名。

#### Scenario: AD 查询缓存营养品
- **WHEN** 用户确认「查询上一次营养品（备注 AD）」且模板播报成功
- **THEN** 写入缓存的 SHALL 为 `op=read`、营养品 `event_id`、`remark_keyword=AD`
- **AND** MUST NOT 缓存事件名为 AD
