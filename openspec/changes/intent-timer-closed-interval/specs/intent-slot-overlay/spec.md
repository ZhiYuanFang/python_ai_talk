## ADDED Requirements

### Requirement: 起止双钟点不触发多钟点降级
当原文可解析为单段计时的起止（恰好两个钟点，或含「到/至/～」等起止连接），且当前 `events` 长度为 1 时，槽位覆盖 SHALL 将两钟点写入该子项的 `start_time`/`end_time`，MUST NOT 因此取消缓存命中并强制分类。当钟点不少于 3 个且 events 长度为 1 时，系统仍 SHALL 强制降级分类（多段喂养）。

#### Scenario: 八点到八点半不降级
- **WHEN** 缓存命中单条计时 create
- **AND** 用户说「8点到8点半母乳」
- **THEN** 系统 SHALL 保持可免确认执行路径（若原已命中）
- **AND** 该子项 start_time/end_time SHALL 对应该两钟点

#### Scenario: 三钟点仍降级
- **WHEN** 原文含三个及以上钟点且 events 长度为 1
- **THEN** 系统 SHALL 取消缓存免确认并进入分类路径

### Requirement: 时长与钟点组合覆盖闭合区间
槽位覆盖（及分类后同等规则回填若适用）SHALL 能抽取「N分钟/N分」时长，并与 0/1 个钟点组合成闭合 `start_time`/`end_time`：有钟点则 start=钟点、end=start+时长；无钟点则 start=now−时长、end=now。

#### Scenario: 覆盖母乳十分钟无钟点
- **WHEN** 缓存命中母乳计时 create 且用户说「母乳10分钟」
- **THEN** 覆盖后 end_time − start_time SHALL 约为 600 秒
- **AND** end_time SHALL 接近当前时刻
