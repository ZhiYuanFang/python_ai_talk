## Why

成长轨迹最终 Markdown 以注意事项为主体、变化描述笼统，且禁止有序展开，家长看不到「未来数日最可能发生什么」的清晰阶梯。补问也缺少「摸清当前能力边界」的策略，且 `enough` 可直跳 generate 跳过末轮自由描述。需要把产出改成有序可能变化主段，并强化提问与必经 free_text 兜底。

## What Changes

- **生成**：主段为编号发展阶梯（可观察的可能变化、按先后/可能性排序）；继续禁止「第 N 天」日历日程；总长约 400～600 字；注意事项/喂养为辅。
- **system**：去掉过紧的约 200 字硬顶，改为与上述长度一致的约束。
- **plan**：优先挖清当前里程碑与能力边界；choice 仍恰好 2 选项；细挖用 free_text。
- **编排**：进入 generate 前 MUST 完成一次 `final_free_text`（含 `enough` 早停路径，不得直跳 generate）。

## Capabilities

### New Capabilities

- `growth-trajectory-ordered-changes`: 有序可能变化主段、字数放宽、提问策略与必经末轮 free_text。

### Modified Capabilities

- （无；基线尚未收录成长轨迹能力；本变更新增上述 capability。）

## Impact

- 代码：`prompts/system.py`、`prompts/generate.py`、`prompts/plan.py`；`plan_next` / `route_after_plan`（enough → final_ask）。
- 产品：会话在生成前多一次自由补充问；Markdown 结构与字数变化。
- 不改：窗长拉取、喂养史 compact、Flutter 契约字段名（若仅消费 Markdown 文本则兼容）。
