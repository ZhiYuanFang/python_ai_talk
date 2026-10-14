## Why

查史句如「昨天拉了几次屎」在段 TIME 维仍会调 TIME LLM 并写入规则缺口，却因 `allow_flywheel=False` 不进时间飞轮；而「昨天」整日窗本可用本地规则（`parse_day_word_window`）算上海日历 unix，不必 LLM。同时时间飞轮仅非 read 读写，阻碍「数据够后各轨 TIME 热路径免 LLM」。另需独立收件箱：在最终无法识别类回复前落原话与用户信息，供 Hub 查删以发现覆盖盲区——不得与 rule_gap / 时间飞轮混用。

## What Changes

- **日词规则前移**：段 TIME 对仅日词（今天/昨天/前天/本周等、无钟点）优先本地填窗，跳过 TIME LLM，且不得因此写入 rule_gap。
- **时间飞轮全轨**：create/read/update/delete 凡需相对时间解析时，同等读写 `feeding_time_cues`（合法相对配方）；点查 `ignore_time_range` 仍可跳过时间窗。移除「仅非 read 才飞轮」限制。
- **热路径目标**：日词规则或飞轮高置信命中时 TIME 维 MUST NOT 调 TIME LLM；LLM 仅冷路径并回写配方，使数据增长后趋近零 LLM（不承诺 100%）。
- **答不出 inbox（独立）**：发出无法识别/暂不支持等终局失败回复前，落问答记录（原话、用户侧标识、失败回复、时间等）；Hub 可列表/删除；MUST NOT 写入 rule_gap 或 time 飞轮。

## Capabilities

### New Capabilities

- `intent-time-dayword-local`：段级日词本地窗、免 TIME LLM、免假缺口
- `intent-time-flywheel-all-rails`：时间相对配方飞轮对各 CRUD 轨同等读写与热路径免 LLM
- `agent-miss-inbox`：终局无法回答前的问答落库与 Hub 查删（独立于 rule_gap / time 飞轮）

### Modified Capabilities

- （无基线独立 capability 文件夹时以本 change 新增为准；实现上衔接既有 `time_cue_store` / `parse_day_word_window` / `rule_gap` 行为收缩）

## Impact

- `app/feeding/services/segment_multidim.py`、`dim_resolve.py`：日词优先、`allow_flywheel` 全轨
- `app/shared/history_window.py`：复用/微调日词窗
- `app/feeding/services/time_cue_store.py`、`/v1/admin/time-cache`：行为不变或小扩说明
- 新 store + `/v1/admin/...` miss inbox；兄弟仓 Hub 列表/删页
- `rule_gap`：日词命中路径不再记 time 缺口
- 不改 clinic；禁止测试文件
