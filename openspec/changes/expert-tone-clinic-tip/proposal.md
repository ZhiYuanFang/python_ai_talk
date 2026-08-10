## Why

clinic / tip 提示词叠了闺蜜人设、对话必点、同月龄代入、引导抛话头与无史「征求肯定」等多套规则，偏长且口语陪伴感过重。产品需要改为简洁的**育儿专家**回答：避免决断医疗；喂养记录有则必点；陪伴对话仅可参考、不强制点名；**不再引导征求肯定**。

## What Changes

- **BREAKING（人设）**：tip / clinic（含 intent 走 `clinic_answer` 的路径）系统提示词由「懂娃闺蜜」改为「育儿专家」口吻；去掉闺蜜式接情绪剧本与「我家要是这月龄…」同月龄代入硬要求。
- **BREAKING（有据规则）**：有注入的喂养记录时仍 **MUST** 点名 1 条相关事实；有 `chat_context` 时 **MUST NOT** 再要求必须点名「上次对话」（可作背景，禁止编造）。
- **BREAKING（收尾）**：去掉无史路径「收尾征求肯定 / 是否说得对」类硬约束；不要求为隐式反馈而引导家长表态。
- 同步精简 system / closing / user 块文案（clinic 与 tip 对齐同一套原则）；保留不做诊断、不开药、点查/汇总以记录为准、无据不编造记忆。
- 引导式抛话头（开放问/二选一）改为非强制或不写入硬约束，避免整套「闺蜜对话感」回潮。

## Capabilities

### New Capabilities

- `parenting-expert-prompts`: clinic/tip 育儿专家提示词口径——简洁、非医疗决断、记录必点、对话非必点、无征求肯定

### Modified Capabilities

- `bestie-companion-persona`: 角色从闺蜜改为育儿专家（仍非医生诊疗定位）
- `grounded-bestie-prompts`: 对话不再强制点名；记录仍强制；人设改为专家
- `bestie-dialogue-hooks`: 去掉强制引导抛话头与同月龄代入硬要求；有据规则与专家口径对齐
- `intent-companion-bridge`: `call_clinic_agent` 使用与 stream 一致的专家版 `clinic_answer`（不再写「闺蜜模板」）

## Impact

- **代码**：`app/clinic/graphs/nodes/prompts/clinic_answer.py`、`app/tip/graphs/nodes/prompts/tip_answer.py`（system / closing / 历史与对话块说明文案）
- **行为**：回复更偏专家说明、更少「上次你说」与收尾求认可；有喂养记录时仍会点数据
- **隐式反馈**：不再靠「征求肯定」话术诱导表态；既有 implicit feedback 节点逻辑可保留但提示词不驱动征求
- **非目标**：不改 HTTP 路径；不改 needs_history 图结构；不恢复通识硬塞；不改 care_alert
