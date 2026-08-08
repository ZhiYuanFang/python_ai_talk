## Why

care_alert 将近史以 JSON 全量注入提示词，条数与字段过多，浪费 token。只需今昨流水做「是否留意」判定，并用独立名→id 表供回填 `eventId`，史行内不带 id。

## What Changes

- 历史注入改为**今天+昨天**窗口的紧凑行：`{相对startTime}{eventName}{后缀}`（计时=秒、计数=eventNumber、一次=「一次」）。
- 另附去重 **eventName=eventId** 对照表；史行 **不得** 带 eventId。
- `startTime` 继续相对中文（刚刚/分钟前/今天/昨天…）。
- care_alert 拉取窗口收窄为近两日（如 `last_2_days`），降低拉取与注入量。
- 通识条数与 clinic 一致：走全局 `knowledge_prompt_top_k`（默认 1），不做 care_alert 专属覆盖。
- 不再对 care_alert 使用 `json.dumps(slim_history…)` 全量 JSON。

## Capabilities

### New Capabilities

- `care-alert-compact-history`: 护理留意近两日紧凑史注入与名 id 对照表。

### Modified Capabilities

- （无基线 capability 强制 MODIFIED；若收版时并入 care-alert 相关叙述即可。）

## Impact

- `app/care_alert/graphs/nodes/prompts/care_alert_analyze.py`、可选 shared 格式化辅助、`analyze.py` data_requirement、`fetch_history` 增加 `last_2_days`。
- tip/clinic 提示词默认不变。
