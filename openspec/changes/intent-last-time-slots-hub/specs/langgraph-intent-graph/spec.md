## ADDED Requirements

### Requirement: 缓存命中后经槽位覆盖再路由
意图分析图在 `match_intent_cache` 高置信命中后，SHALL 先执行槽位覆盖节点（如 `overlay_slots`），再进入既有读历史 / 落库 / 结束路由。当槽位覆盖判定须降级分类时，图 SHALL 视为缓存未命中并进入 `in_progress_probe` → `classify_intent`（或等价）链路，MUST NOT 带着未覆盖的单条缓存结果免确认落库。

#### Scenario: 命中后先覆盖
- **WHEN** `match_intent_cache` 返回命中且无需因多钟点降级
- **THEN** 图 SHALL 在执行 CRUD 或 speak 之前完成 clock/qty 覆盖

#### Scenario: 降级后进分类
- **WHEN** 槽位覆盖判定多钟点对单条 events
- **THEN** 图 SHALL 进入分类路径
- **AND** `need_confirm` 行为 SHALL 遵循分类路径默认确认规则
