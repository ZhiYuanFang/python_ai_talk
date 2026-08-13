## ADDED Requirements

### Requirement: filter 支持备注模糊且与事件 AND
`GET /device/history/api/filter` SHALL 增加可选 `remark` 查询参数。当 `remark` 去空白后非空时，系统 SHALL 在既有 deviceNo / eventIds / 时间窗 / limit 条件上 **AND** `remark LIKE %keyword%`（先转义 `%` 与 `_`）。`history.remark` MUST 保持可空；NULL 与空串表示无备注，模糊条件 MUST 排除这些行。系统 MUST NOT 把 `remark` 列改为 `NOT NULL`。

#### Scenario: 事件加备注正式点查
- **WHEN** 客户端以 `deviceNo`、`eventIds` 为营养品 id、`remark=AD`、有效 Unix 窗调用 filter
- **THEN** 返回行 SHALL 均为该事件且备注包含 AD
- **AND** 备注为 NULL 或空串的行 MUST NOT 出现

#### Scenario: 无备注参数行为不变
- **WHEN** 客户端不传 `remark` 或传空串
- **THEN** 筛选行为 SHALL 与加字段前一致（不按备注过滤）

### Requirement: 无事件 ID 的备注查询仅作探针
当 `remark` 非空且 `eventIds` 为空时，该请求 SHALL 视为备注探针：`limit` MUST 被限制为不超过 20（调用方更小则取其值），建议带时间窗。该路径用于定事件，MUST NOT 作为把全量原始史注入 LLM 的借口。

#### Scenario: 探针有上限
- **WHEN** 客户端以 `remark=AD`、`eventIds` 空、`limit=100` 调用 filter
- **THEN** 系统 SHALL 最多返回 20 条
- **AND** 结果按 id 倒序

### Requirement: 字典外词经备注探针定为已知事件
当点查句式中的专名不在事件字典时，系统 MUST NOT 将其当作新事件类型。系统 SHALL 先用备注探针（小 limit）按设备历史聚合命中事件，只把一行摘要注入分类（不得注入原始行列表），再由分类输出字典 `event_id` 与 `remark_keyword`，并确认后正式拉史。

#### Scenario: 上一次吃的 AD
- **WHEN** 用户问「上一次什么时候吃的 AD」且近窗备注含 AD 的记录均落在营养品
- **THEN** 分类或确认话术 SHALL 使用字典名「营养品」而非事件名「AD」
- **AND** 确认文案 SHALL 询问是否查询上一次吃的营养品（按备注 AD）
- **AND** 确认前 MUST NOT 把全类型原始 history 注入分类 prompt
- **AND** 确认后正式 filter SHALL 带营养品 `eventIds` 与 `remark=AD`

#### Scenario: 探针零命中仍禁止新建事件
- **WHEN** 备注探针无命中
- **THEN** 系统 MAY 用常识给出候选字典事件并确认
- **AND** MUST NOT 设置 `is_new_event` 并创建 AD 事件类型
- **AND** 确认后正式查询仍无行时 `content` SHALL 说明最近没有备注里带该词的对应事件

#### Scenario: 光说 AD 先分读写
- **WHEN** 用户只说「AD」且无查询句式、无 pending
- **THEN** 系统 SHALL 确认是记录一笔营养品（备注 AD）还是查询上一次
- **AND** SHALL NOT 直接建新事件或拉全量史

### Requirement: 可复制 DDL 不改变备注可空
兄弟仓 SHALL 提供可手工执行的 SQL 文件，为 `history` 增加支撑 filter 的复合索引，并可选增加备注 FULLTEXT（ngram）。该脚本 MUST NOT 将 `remark` 改为 `NOT NULL`。运维复制执行；应用启动 MUST NOT 自动改表。

#### Scenario: SQL 保持可空
- **WHEN** 运维阅读并执行该 SQL
- **THEN** 脚本中 SHALL 明确 remark 保持可空
- **AND** SHALL NOT 包含把 remark 改为 NOT NULL 的语句
