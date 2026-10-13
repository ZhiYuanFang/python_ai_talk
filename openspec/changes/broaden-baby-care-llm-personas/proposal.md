## Why

feeding 段维多维 LLM 人设普遍写成「母婴喂养…」，易把领域收窄成只吃奶；而产品覆盖睡眠、换尿布、营养品、疫苗等宝宝照护落库事件。OP 纠偏里「非喂养闲聊 → other」更易误伤非喂养类记录句。需统一放宽人设并纠正 other 边界。

## What Changes

- feeding 内所有相关维 LLM system / 内联人设，由「母婴喂养」改为 **宝宝照护记录**（明示含喂养、睡眠、换尿布、营养品、疫苗等可落库事件）。
- OP 轨 other：改为「与宝宝照护记录无关的闲聊/无关」；删除「非喂养」表述；语义例可补换尿布/营养品/疫苗 → create。
- 覆盖：`prompts/system.py` 各 SEGMENT_* / HISTORY_SPEAK / PENDING 等，以及 `dim_resolve` 内预测两维、定位策略内联人设。
- 满血分类模板已是「事件意图分析助手」：MAY 补一句领域说明，不强制大改。
- **不改**模块名 `feeding`、API、CRUD 契约、播报模板、事件字典本身。

## Capabilities

### New Capabilities

- `intent-llm-domain-persona`：feeding 意图相关 LLM 人设与 other 边界须覆盖宝宝照护全记录域，不得仅限喂养

### Modified Capabilities

（无强制修改基线其它 capability 的 Requirement 标题；行为增量落在上列新 capability。）

## Impact

- Python：`app/feeding/graphs/nodes/prompts/system.py`、`app/feeding/services/dim_resolve.py`（及同类内联人设若审计发现）
- 提示词文案变更；无 schema / Go / Hub 强制
