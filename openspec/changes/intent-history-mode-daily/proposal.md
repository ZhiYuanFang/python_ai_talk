## Why

宝妈除养育建议外，还常问「今天喂了几次」「一共多少毫升」「和昨天比少了吗」。intent 查史默认 `history_mode=point`（上一次模板），分类提示未暴露/约束 `history_mode`，区段汇总与事实对比落不到已有 `daily` 紧凑播报。养育建议与含糊「最近怎么样」应归 clinic，intent 不得装作分析建议。

## What Changes

- 分类 JSON / 提示增加顶层 `history_mode`：`point` | `daily`，并写清选用规则。
- **point**：上次/上一次/最近一次等点查（配合 `ignore_time_range=true`）。
- **daily**：今天/昨天/本周等区间 + 几次/一共/吃了什么/相邻日事实增减等 → `ignore_time_range=false` + 时间窗；`speak_history` 走已有 daily 紧凑行（含总量/次数与相邻日 Δ 摘要）。
- **养育建议**与含糊「最近怎么样」：intent MUST NOT 用 history 装建议；归 clinic（本仓分类产出 `conversation` 并给出简短引导文案，或保持可被上游识别的语义；**不**在 intent 图内调用 clinic）。
- 区段 daily 查询适当提高默认/提示 `limit`，降低一周窗被 20 条截断的风险。
- **不改**：CRUD 主路径、point 模板正文、clinic 内部逻辑；**不**做「改删按历史行精确定位」（另 change）。

## Capabilities

### New Capabilities

- （无）

### Modified Capabilities

- `intent-analysis`: 分类须产出 `history_mode`；点查/日汇总/建议拒识分流
- `intent-history-query`: daily 须由分类驱动；事实区段播报；建议类不走装懂查史

## Impact

- **本仓**：`INTENT_CLASSIFICATION_SYSTEM_TEMPLATE`、classify 解析保留 `history_mode`/`limit`、`speak_history`（已支持 daily，确认透传）。
- **clinic / 兄弟仓**：intent 不调 clinic；「最近怎么样」依赖产品上游或 conversation 引导用户走 `/v1/clinic`。
- **关联**：复用 `build_feeding_history_prompt_blocks`；与 `unify-feeding-history-compact` 衔接。
