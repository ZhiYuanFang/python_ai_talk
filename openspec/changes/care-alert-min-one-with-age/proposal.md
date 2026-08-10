## Why

护理留意在「有近两日记录」时仍常返回空 `items`，跑马灯无内容；同时当前提示词允许「史不够就空」，且对**宝宝月龄**的约束不够硬。产品需要：有近两日可分析记录时**尽量/必须至少一条**值得留意，且判定必须结合月龄（同信号在不同月龄含义不同）。

## What Changes

- 有近两日历史（且能回填 eventId 对照表）时：analyze **MUST** 产出至少 1 条 item；无历史或无法可靠回填 eventId 时仍允许 `items=[]`。
- 提示词（本地 bootstrap `output_format` + 运行时 user 指引）改为：禁止在有史时轻易空列表；**必须结合宝宝月龄**选择/解释留意点（月龄未知时显式按未知处理，不得假装已知月龄通识）。
- 弱信号时仍可出项，但语气偏轻、score 可偏低；与对比样例冲突时以「有史至少一条 + 月龄条件」为底线，样例用于调节强弱而非全部压成空。
- 可选后处理兜底：LLM 在有史+legend 仍返回空时，按月龄与史信号合成一条软提醒（保证契约），避免只靠模型听话。
- 更新相关 CONTRACT / 模块注释口径（准确优先 → 「有史保底一条 + 月龄」）。

## Capabilities

### New Capabilities

- `care-alert-min-one-with-age`: 有近两日记录时至少一条留意；判定与兜底必须纳入宝宝月龄

### Modified Capabilities

- （无基线 `openspec/specs/` 内已收版 capability 需改写；本变更与未收版的 `care-alert-prompt-flywheel` 叠加，收版时以本能力覆盖其「有史仍可空列表」口径。）

## Impact

- **代码**：`prompt_store` 默认 `output_format`、`care_alert_analyze` user 文案、`generate_care_alerts`（可选兜底）、已落盘 `prompt.json` 的 bootstrap/迁移说明
- **API**：请求/响应外形不变；有史时 `items` 长度期望从「可 0」变为「≥1」
- **飞轮**：对比样例仍生效，但不得把「有史必空」教给模型；弱信号策略改为轻提而非禁提
- **非目标**：不恢复通识检索；不要求无历史时也硬出一条；不改 Go/Flutter 字段枚举
