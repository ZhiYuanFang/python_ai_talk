## Why

有据点名后的闺蜜回复仍偏单向安慰，缺少把球踢回家长的引导，对话感弱。需要在提示词中强化「文末引导式话题」与「同月龄闺蜜代入」，并把篇幅从约 50 字放宽到约 80 字，使点查/建议都能形成实质来回。

## What Changes

- Clinic 与 tip 的 system/user 提示增加：尽可能在回应末尾追加一句引导式话题（开放问或轻二选一），含**点查**与汇总（先答准事实再引导）。
- 月龄已知时可模拟「我家要是也这月龄，我可能会…」作共鸣；月龄未知不编同月龄；代入不得冒充对方喂养记录。
- 建议/闲聊/ tip 开场目标字数由约 **50 → 约 80**；点查/汇总仍以念清时间为先，尽量压在约 80 字附近。
- 保留既有有据点名、无据不编、安全（不诊断/不开药）规则。
- **不**改编排、检索、Q&A 捷径。

## Capabilities

### New Capabilities

- `bestie-dialogue-hooks`: clinic/tip 提示词的引导式收尾、同月龄代入与约 80 字预算。

### Modified Capabilities

- （无已归档基线；在既有 grounded-bestie 提示行为上增量，本 change 用新 capability 描述。）

## Impact

- `app/clinic/graphs/nodes/prompts/clinic_answer.py`
- `app/tip/graphs/nodes/prompts/tip_answer.py`
- 相关单测（更新 50→80 与新约束短语断言）
- API/图结构：无变更
