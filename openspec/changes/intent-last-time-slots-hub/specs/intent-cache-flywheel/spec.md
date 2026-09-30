## ADDED Requirements

### Requirement: 意图缓存骨架不冻结绝对开始时间
写入意图缓存（含运行时成功后写入与管理端批量种子）时，对 create 类载荷系统 SHALL NOT 将某次执行时的绝对 `start_time` 作为可复用骨架长期冻结（写入前剥离或置空）。数量字段 MAY 保留作默认；本轮槽位覆盖或分类结果优先。查记录类缓存的时间窗字段不受本条强制清空（若业务需要可保留）。

#### Scenario: 再次命中不复用旧绝对时刻
- **WHEN** 用户曾确认「记录吃了120毫升配方奶」且写入缓存时执行时刻为 T1
- **AND** 之后用户再说无钟点的高度相似句并缓存命中
- **THEN** 落库所用 startTime SHALL 为覆盖后的本轮时间或执行时 now
- **AND** MUST NOT 静默复用 T1 作为 startTime
