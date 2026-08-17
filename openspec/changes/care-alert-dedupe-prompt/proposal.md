## Why

护理留意 system（`prompt.json` output_format）与 user（`care_alert_analyze`）重复写了「至少一条 / 空列表 / 月龄 / 对比样例 / eventId」等规则，拉长 token；且 system 仍写「近两日、只今天昨天」，与近期日历日史口径漂移。需要消重并压缩 system，让政策只在一处、user 只带实例。

## What Changes

- **A（瘦 user）**：`build_care_alert_user_message` 删除与 system 重复的政策长段与 `age_hint`；仅保留月龄/性别/逻辑日、近期史、legend、可选摘要；可保留一句「按系统判定与输出格式作答」。
- **B（压缩 system）**：重写 `default_output_format`：合并【判定依据】与文末「规则」中的重复点；「近两日」统一为「近期记录」；去掉「只参考今天与昨天」。
- 提升 `PROMPT_DOC_VERSION`，迁移时覆盖 `output_format`、保留 `contrastive_examples`。
- 更新飞轮实例检测正则（「近两日记录」→ 兼容「近期记录」），避免拦不住错误落盘。
- 仓库内 `data/care_alert/prompt.json` 随默认模板对齐（若存在）。

## Capabilities

### New Capabilities

- `care-alert-prompt-dedupe`: system 为唯一政策源且经压缩；user 仅运行时实例数据，不复述判定规则。

### Modified Capabilities

- （无强制改既有 capability 名；min-one / compact-history 行为不变，仅提示词载体消重。）

## Impact

- `app/care_alert/graphs/nodes/prompts/care_alert_analyze.py`
- `app/care_alert/services/prompt_store.py`（default_output_format、版本、校验正则）
- `data/care_alert/prompt.json`（本地投影）
- 飞轮对比样例逻辑不变；analyze API 契约不变
