## ADDED Requirements

### Requirement: 缓存命中后覆盖钟点与数量
当意图缓存高置信命中且进入免确认执行路径前，系统 SHALL 从本轮用户原文用轻量规则抽取钟点（clock）与数量（quantity），并覆盖到缓存 `events[]` 对应字段后再执行。覆盖 MUST NOT 修改 `op`、`event_id`、`action` 等骨架字段。数量抽取 MUST 优先匹配带毫升/ml/「吃了」等上下文的数字，MUST NOT 把「X点」中的小时数字误当作数量。

#### Scenario: 单条种子覆盖五点与毫升
- **WHEN** 缓存文档为「记录吃了120毫升配方奶」且 payload 为单条配方奶 create
- **AND** 用户说「记录5点吃了120毫升配方奶」且缓存命中
- **THEN** 系统 SHALL 将 `events[0].start_time` 设为当日（Asia/Shanghai）5 点对应 Unix 秒（或语义等价）
- **AND** quantity 保持或覆盖为 120
- **AND** 落库 startTime MUST NOT 默认为「现在」而忽略已抽取的 5 点

#### Scenario: 无钟点则不强制改时间
- **WHEN** 缓存命中且原文无钟点词
- **THEN** 系统 MAY 保持 payload 中空的 start_time，执行层按现有规则用当前时间
- **AND** MUST NOT 因本条凭空写入错误历史钟点

### Requirement: 多钟点对单条事件强制降级 LLM
当规则从原文抽到不少于两个钟点，且缓存（或当前 intent）`events` 长度等于 1 时，系统 SHALL 取消本次缓存免确认命中，改为走分类 LLM 路径（可再确认）。系统 MUST NOT 在该情况下用单条事件硬盖多个钟点，也 MUST NOT 在覆盖节点内擅自拆成多条 events。

#### Scenario: 三钟点一句对单条种子
- **WHEN** 用户说含今天 5 点、7 点、8 点三次喂养的句子
- **AND** 向量命中仅含一条 create 的种子
- **THEN** 系统 SHALL 不按该缓存免确认执行
- **AND** SHALL 进入 classify_intent（或等价分类）路径
