## Why

Clinic/tip 虽有「闺蜜」人设，但建议/闲聊场景常只空共情，不点名近期对话或喂养记录，家长感受不到「我记得、我懂你」；有注入依据时也未强制落入口语正文。需要用提示词约束：有据必点名、无据不编造，并保持约 50 字内的短回复。

## What Changes

- 强化 clinic（及 tip）回答 system/user 提示：有经验闺蜜态度；有 `chat_context` 须点到上次相关内容；有喂养历史须点到与本轮相关的一条记录事实，再给对应回应。
- 去掉或改写「知识与记录只作背景」等与「有据必用」冲突的表述；点查/汇总既有硬规则保留并与「点名依据」对齐。
- 无喂养记录且无近期对话时：禁止编造「上次/记录里」；可短陪，诚实说明没翻到依据（若需要）。
- 正文目标约 **50 字内**；有据时只挑最相关 1 条，不堆砌。
- **不**改图路由、向量门槛、闲聊跳过检索；Q&A 捷径命中路径不走本提示时注明为例外（本 change 不强制改捷径答案）。

## Capabilities

### New Capabilities

- `grounded-bestie-prompts`: clinic/tip 生成提示词要求有经验闺蜜口吻、有对话/历史则点名依据再答、无据不编、约 50 字。

### Modified Capabilities

- （无已归档基线 specs；本 change 以新 capability 覆盖提示词行为。）

## Impact

- `app/clinic/graphs/nodes/prompts/clinic_answer.py`（及同步生成/流式共用该提示）
- `app/tip/graphs/nodes/prompts/tip_answer.py`（同气质，事件开场点近况）
- 可选：极轻量单测断言提示词含关键约束文案
- API/图结构/检索逻辑：无变更
