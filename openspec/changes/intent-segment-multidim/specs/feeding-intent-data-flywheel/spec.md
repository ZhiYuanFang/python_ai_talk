## REMOVED Requirements

### Requirement: 系统在用户确认LLM解析意图后添加用户表达
**Reason**: 整句用户表达绑定单一事件的数据飞轮已由「段级短说法 → 事件」飞轮替代；禁止再把复合整句写入为可整包回放单位。
**Migration**: 使用 `intent-event-phrase-flywheel`：确认后仅写短说法；集合可清空重建。

### Requirement: 系统设置向量库最大记录数
**Reason**: 容量与清理策略随事件说法库重定，不再沿用本条 10,000/90% 旧口径作为整句表达飞轮约束。
**Migration**: 事件说法库清理策略在实现中沿用或调整质量分/低分清理；不以本基线条目为准。

### Requirement: 系统计算向量数据质量评分
**Reason**: 与上条一并退出整句表达飞轮质量模型。
**Migration**: 若事件说法库保留 quality_score，按其新语义实现，不继承本条计算公式为强制验收。

### Requirement: 系统记录向量数据的匹配计数和成功计数
**Reason**: 旧 match_count/success_count 整句飞轮计数模型废弃。
**Migration**: 事件说法库可以有独立计数；不以本条为强制。
