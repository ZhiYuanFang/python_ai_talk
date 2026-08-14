## Why

分类后图边恒定进入 `resolve_remark_event`，节点内无未定名称时再空返回。读图像「每轮都反查」，且流式会多一次「正在按备注对照事件…」thinking。条件应在 `route_after_classify` 判断；反查节点只处理真正的备注定事件。

## What Changes

- `route_after_classify`：存在「有 event_name、无 event_id」的顶层或 `events[]` 槽位时，才路由到 `resolve_remark_event`；否则直接走与现 `route_after_remark_resolve` 相同的确认/执行/查记录分支。
- `resolve_remark_event`：假定已有未定名称，专注字典再匹配失败后的 Go 备注反查（唯一命中 / 多命中消歧 / 零命中无法识别）；去掉「无槽位则空返回」作为图路径上的主依赖（可保留防御性早退）。
- 未定名称判定逻辑抽出共享（供路由与节点一致），避免两边漂移。
- **非目标**：不改备注反查成功/失败语义；不恢复分类前备注探针；不写测试。

## Capabilities

### New Capabilities

- （无）

### Modified Capabilities

- `langgraph-intent-graph`：分类后条件边仅在字典未命中名称时进入备注反查节点；无未定名称时跳过该节点。
- `history-remark-filter`：明确反查步骤由路由条件门控，节点只执行反查。

## Impact

- **代码**：`intent_graph.py`、`resolve_remark_event.py`（导出/共享未定槽位检测）；思考文案仅在真正进入反查节点时出现。
- **行为**：HTTP 与定事件结果不变；无未定名称路径少一次节点与 thinking。
- **API**：无契约变更。
