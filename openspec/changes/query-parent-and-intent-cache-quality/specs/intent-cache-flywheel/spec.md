## MODIFIED Requirements

### Requirement: 意图缓存是意图路径唯一向量匹配
当意图缓存 **相似度** 达到实现所定高置信阈值 **且** 该条 **质量分** 达到实现所定下限时，系统 SHALL 采用缓存中的 `op` 与 `events` 作为意图结果。系统 MUST NOT 再查询 `feeding_events` 或任何事件名向量以覆盖该结果。相似度不足、质量分不足、或短窗内对刚免确认执行过的同一问再问，SHALL 进入未命中路径（可先备注探针再分类），SHALL NOT 降级到事件名 Top-1。

#### Scenario: 缓存命中跳过分类
- **WHEN** 用户再次输入与已缓存多事件原话高度相似的句子
- **AND** 该条质量分不低于下限
- **AND** 并非同一设备短窗内对刚免确认执行过的同一问
- **THEN** 系统 SHALL 复述缓存的多事件 `create` 结果进入执行层
- **AND** SHALL NOT 再检索事件名向量

#### Scenario: 质量分不足当未命中
- **WHEN** 最相似缓存条相似度达到高置信阈值
- **AND** 其质量分低于下限
- **THEN** 系统 SHALL 视为未命中
- **AND** SHALL 进入分类（可先备注探针）
- **AND** SHALL NOT 免确认执行该条载荷

## ADDED Requirements

### Requirement: 意图缓存条目带质量分
`feeding_intents` 每条 MUST 在顶层 metadata 保存 `quality_score`（不得只放在 payload JSON 内）。新写入默认 0.8。检索命中判定 MUST 同时检查相似度与质量分（质量下限 0.7，缺省元数据按 0.8）。同一 document 已存在时 MUST 更新该条而非另写 uuid 分身。

#### Scenario: New cache row has quality
- **WHEN** 用户确认查记录或落库成功并写入意图缓存
- **THEN** 该条 metadata SHALL 含 `quality_score`
- **AND** 初始值 SHALL 为 0.8

### Requirement: 短窗重复同一问扣分并当未命中
系统 SHALL 按设备记住最近一次 **意图缓存免确认执行** 的问句与向量 id（滑动短窗，默认 3 分钟）。当同一 `device_no` 在窗内再次提交同一问（规范化后相等）且将命中该缓存时，系统 MUST 将该条 `quality_score` 减少 0.2（不低于 0），MUST 视为未命中并走分类确认，MUST NOT 再次免确认执行。窗口外再说同一句 MAY 正常命中。未确认路径 MUST NOT 因本条写入新缓存。

#### Scenario: Immediate repeat after cache skip-confirm
- **WHEN** 缓存高置信命中并已免确认执行
- **AND** 同一设备在短窗内再次输入同一问
- **THEN** 系统 SHALL 降低该缓存条质量分
- **AND** SHALL 进入未命中逻辑（分类且需确认，除非随后再次命中其他达标条）
- **AND** SHALL NOT 本轮再次免确认执行原载荷

#### Scenario: Next day same question still hits
- **WHEN** 用户隔日再说已缓存且质量分仍达标的同一问
- **AND** 短窗已过期
- **THEN** 系统 MAY 免确认采用缓存

### Requirement: 查父缓存存父 id 不存展开叶子列表
当查记录因父事件确认并成功播报后写入缓存时，载荷 MUST 使用父事件的 `event_id` / `event_name` / `event_ids`（父 id），MUST NOT 把展开后的子孙叶子 id 列表当作可复用查询目标。下次命中后系统 MUST 再展开叶子拉史。

#### Scenario: Diaper query cache keeps parent id
- **WHEN** 用户确认查询换尿布并模板播报成功
- **THEN** 写入缓存的 SHALL 为 `op=read` 与父事件换尿布的 id
- **AND** MUST NOT 仅缓存尿尿与拉屎两个叶子 id 作为下次直接分别点查目标

### Requirement: 定时清理低质量意图缓存
系统 SHALL 定期删除 `feeding_intents` 中 `quality_score` 低于 0.3 的条目。清理 MUST NOT 删除或清空 `mother_baby_knowledge` 或其他非意图缓存 Collection。

#### Scenario: Low score intent row removed
- **WHEN** 定期清理任务运行
- **AND** 某 `feeding_intents` 条目质量分低于 0.3
- **THEN** 系统 SHALL 删除该条目
- **AND** SHALL NOT 因此删除知识库文档
