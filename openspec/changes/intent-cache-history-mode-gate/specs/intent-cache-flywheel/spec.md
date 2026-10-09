## ADDED Requirements

### Requirement: 查史缓存命中须通过 history_mode 门闩
当意图缓存近邻分数与质量分达标，且载荷为查史（含 `op=read` 或等价 history）时，系统在接受命中并跳过分类之前 MUST 用本轮用户原文的轻量语义线索与载荷 `history_mode`（`point`|`daily`；缺省视为 `point`）比对。当原文强线索指向 daily 而载荷为 point（或强线索指向 point 而载荷为 daily）时，系统 MUST 视为未命中并进入分类（或等价）路径，MUST NOT 免确认沿用该载荷。同 mode 线索一致或原文无明显 point/daily 强线索时，SHALL 允许照常命中以保留飞轮。

#### Scenario: 今天几次不得命中上一次点查缓存
- **WHEN** 用户说「今天喝水几次」（或语义等价的区间次数问）
- **AND** 向量近邻命中一条 `history_mode=point`（或未设 mode）的喝水查史缓存
- **THEN** 系统 SHALL 拒绝该命中
- **AND** SHALL 继续走分类 LLM（或图内等价分类路径）

#### Scenario: 同几次问法可复用 daily 缓存
- **WHEN** 用户再次说「今天喝水几次」
- **AND** 近邻命中 `history_mode=daily` 的查史缓存且分数质量达标
- **THEN** 系统 SHALL 允许命中并跳过分类

### Requirement: 查史写入改写文档须区分 point 与 daily
`rewrite_standalone_document`（或等价）在为 `op=read` 生成缓存文档时，当 `history_mode=daily` 时 MUST 使用区段/次数类独立句模板，MUST NOT 写成「上一次{事件}是什么时候」。当 `history_mode=point` 或缺省时，MAY 继续使用「上一次…是什么时候」类模板。

#### Scenario: daily 成功写入不用上一次句式
- **WHEN** 查史成功且 `history_mode=daily` 写入意图缓存
- **THEN** 缓存 document SHALL NOT 为「上一次{该事件}是什么时候」句式
