## Why

分类已能产出 `history_mode=daily`（如「今天喝了几次水」），但查史软确认路径 `create_history_confirm_response` 创建 pending 时未写入 `history_mode`/`limit`；用户确认后 `speak_history` 回落默认 `point`，仍答「上一次…数量为…」而非区段汇总。父消歧 pending 同样未携带这些字段。

## What Changes

- 查史软确认（`create_history_confirm_response`）创建 pending 时 MUST 透传分类结果的 `history_mode` 与 `limit`。
- 父消歧 / 查父确认回填路径 MUST 同样保留并回写 `history_mode`/`limit`（与叶子确认后 restore 对齐）。
- 确认通过后进入 `speak_history` 时，`history_mode=daily` 须真正驱动日汇总播报，不再因 pending 丢字段而回落 point。
- 不改分类提示、不改 Go 拉史契约、不改确认话术文案。

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `intent-history-query`: 查史确认全链路须保留 `history_mode`/`limit`，确认后 daily 不得回落 point 模板
- `feeding-intent-user-confirmation`: 查史 soft confirm / 父消歧 pending 须持久化并回填 `history_mode`/`limit`

## Impact

- **本仓**：`create_history_confirm_response`、`create_parent_disambiguation_pending`（及调用方）、`try_handle_pending` 查父确认拼 fields 分支；`PendingClarification` 已有字段可复用。
- **关联**：修补 `intent-history-mode-daily` 设计中「确认后须带上 history_mode」的缺口。
- **Go / Flutter**：无契约变更。
