## Why

旧路径用「整句意图缓存命中免确认 / 未命中则用户确认再灌飞轮」驱动越用越快。段多维改造后，整包免确认已删除，短说法飞轮只记事件身份；但成功拼装仍默认 `need_confirm=True`，且 `match_source=llm` 强制进 `leaf_confirm`，用户对已判对的「睡醒了→结束睡眠」仍要二次点头。多维规则/小 LLM 已是机器对齐，末轮 yes/no 不再服务旧飞轮，属于冗余闸门。

## What Changes

- 段多维拼装结果在**无阻塞澄清**时：叶子已定、槽位齐（含 number 有量或非 number）、无父消歧/多叶消歧 → **直接执行**（CUD batch / 模板查史），MUST NOT 再发 `leaf_confirm`「您是要…吗？」。
- **仍须用户交互**：父事件消歧、number 缺量追问、备注/别名多叶消歧、拼装失败重说。
- 去掉（或收窄）`match_source == llm` 一律强制确认。
- 短说法飞轮改为**落库/查史执行成功后**按段写入（不再依赖用户点确认）。
- 多段策略 C：无阻塞时同质短拼问改为直接执行多段（或逐段执行），不再拼一句 yes/no。

## Capabilities

### New Capabilities

- `intent-direct-execute-resolved`：拼装完整且无阻塞时直执行；与阻塞澄清、短说法写入时机的边界

### Modified Capabilities

- `feeding-intent-user-confirmation`：完整叶子不再默认 leaf_confirm；策略 C 在无阻塞时直执行
- `intent-segment-multidim`：成功拼装默认 `need_confirm=false`（阻塞项除外）
- `intent-event-phrase-flywheel`：短说法在执行成功后写入，不依赖 leaf_confirm

## Impact

- **Python**：`segment_multidim.drafts_to_intent`、`resolve_segments`、`intent_pipeline`（去掉 llm 强制确认、完整结果走 `_execute_after_confirm` 或等价）、短语写入调用点。
- **体验**：「睡醒了」判对后直接结束计时并回执，不再问「现在结束吗」。
