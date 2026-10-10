## Why

分类已能产出备注专名（如「吃菠菜了」→ 菠菜），但意图信封用 `remark_keyword`、落库 batch 只读 `remark`，导致喂养记录备注为空。双字段无必要：create 写入与 read 筛选在 Go 侧均为 `remark`，Python 应统一为同一字段。

## What Changes

- **BREAKING**：意图信封、图状态、pending、分类提示词、查史/落库/飞轮载荷中 **废除 `remark_keyword`**，一律使用 `remark`（含子项 `events[].remark` 与必要的顶层兼容展示字段若仍需要则亦名 `remark`）。
- create/update/end 落库：`collect_event_items`（或等价）将 `events[].remark`（及约定顶层 `remark`）写入 Go batch 的 `remark`。
- read 拉史：`speak_history` / 备注反查等改为读 `remark`，再传 filter 查询参数 `remark`。
- 分类 system 提示词：字段说明与 JSON 模板只保留 `remark`；语义覆盖「查记录专名」与「create 明细备注」。
- 运行时路径 **不做** `remark or remark_keyword` 回退；运行时源码与分类提示词 MUST NOT 再使用字段名 `remark_keyword`。
- **一次性 Chroma 迁移（仅 feeding_intents）**：env 开关（默认 false）在启动时把 payload 顶层与 `events[]` 中的旧键写入空的 `remark` 并删除旧键；**不**改 MySQL。与 `CLEAR_FEEDING_INTENTS_ON_STARTUP` 同时为 true 时只清空、不迁。

## Capabilities

### New Capabilities

- `intent-remark-field`：意图侧备注字段唯一为 `remark`；create 落库与 read 筛选共用；禁止运行时 `remark_keyword`；可选启动迁移 Chroma 旧键。

### Modified Capabilities

- （无基线已合并条款需 MODIFIED；未收版 change 中若仍写 `remark_keyword`，以本能力为准在实现时一并改代码。）

## Impact

- **python_ai_talk**：信封/提示词/落库/查史/飞轮如上；另 `settings` + `main` 启动钩子 + `intent_cache_store` 迁移方法；`.env.example` 文档化开关
- **Go / MySQL**：无表结构变更；batch 与 filter 本已使用 `remark`；本 change **不**回填已空的 history.remark
- **存量意图缓存**：靠 env 一次性改写 payload；迁完务必关开关