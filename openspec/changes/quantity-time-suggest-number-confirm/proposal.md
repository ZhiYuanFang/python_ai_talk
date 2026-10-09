## Why

用户说「记录60毫升母乳」时，分类常按字面选计时叶子「母乳」，把计量语义落到 `type=time` 上。表内往往另有近义计量叶（如「瓶喂母乳」）。应在 LLM 思考中发现「有 quantity 却命中 time」冲突，改选近义 `number` 叶，并以简洁确认问句（如「您是要记录瓶喂母乳60毫升嘛？」）征求用户，避免直接按计时母乳落库。

## What Changes

- 在意图分类 system 提示中增加通用规则：子项带 `quantity`（毫升等）且若按口语会落到 `type=time` 时，须在事件表中由 LLM 判断近义 `type=number` 叶；有则将 `event_id`/`event_name` 填为该计量叶，并用简洁 `confirm_message` 询问（示例：「您是要记录瓶喂母乳60毫升嘛？」）。
- 「N分钟」等时长不是 quantity，计时补记仍走 time，不触发本规则。
- 近义判定仅由 LLM 完成；不做名称包含/同父等代码近义扫描；不静默免确认落库。
- 冲突改选场景：叶子确认 pending MUST 保留/优先分类产出的 `confirm_message`（非空时不得被模板无条件覆盖）；并约束 LLM 的 `confirm_message` 力求简洁。
- **不改**意图缓存命中路径（本 change 只管 classify LLM）。

## Capabilities

### New Capabilities

- （无）

### Modified Capabilities

- `intent-analysis`: 分类须处理「quantity + 近义 time/number」冲突：改选 number 叶并给出简洁确认问句
- `feeding-intent-user-confirmation`: 冲突改选后的 leaf_confirm MUST 优先使用 LLM 的 `confirm_message`

## Impact

- **本仓**：`INTENT_CLASSIFICATION_SYSTEM_TEMPLATE`；核对 `create_leaf_confirm_pending` / `postprocess` 对 `confirm_message` 的传递与优先。
- **API / 兄弟仓**：无接口变更。
- **缓存 / overlay**：明确不在范围。
