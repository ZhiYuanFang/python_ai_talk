## ADDED Requirements

### Requirement: 确认前用规则覆盖事件时间再生成确认话术
当分类路径（非缓存免确认命中）即将为 CUD 叶子创建确认 pending（含单条 leaf_confirm 与多事件确认）时，系统 SHALL 先用与落库前相同的规则（`apply_time_slots_to_events` 或等价）根据用户原文覆盖 `events[]` 的时间字段（半命中时 MUST NOT 用残缺 clock 覆盖，与槽位半命中行为一致），再基于覆盖后的 `start_time`/`end_time` 与数量生成用户可见确认话术。确认话术中的口语时间 MUST 与即将落库的规则时间语义一致（允许「现在」当无可用钟点时）。

#### Scenario: 分类后确认话术使用规则盖写后的昨晚六点
- **WHEN** 用户说「昨晚6点洗澡了」且分类路径将创建记录确认
- **AND** 规则可完整解析该钟点
- **THEN** 系统 SHALL 在生成确认话术前用规则写入对应昨日 18:00（或语义等价）的时间字段
- **AND** 用户可见确认话术 SHALL 体现该时间（反推日段/钟点），MUST NOT 仅因 LLM 误填今日 06:00 而确认成早上六点

#### Scenario: 半命中确认前不覆盖残缺钟点
- **WHEN** 原文对规则为半命中
- **AND** 即将创建记录确认
- **THEN** 确认前规则覆盖 MUST NOT 用残缺 clock 改写 start/end
- **AND** 确认话术 MAY 按无可用规则钟点处理（如「现在」）或保留未被残缺规则踩掉的既有字段
