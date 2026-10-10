## Context

意图侧并行存在 `remark`（schema 有、落库读它）与 `remark_keyword`（提示词/反查/查史/飞轮用它）。LLM 把「菠菜」写入 `remark_keyword` 后，`collect_event_items` 只组装 `ev.remark`，Go batch 的 `remark` 为空。Go filter/batch 参数名本就是 `remark`。产品要求：统一为 `remark`；运行时不再读旧键；存量 **仅 Chroma `feeding_intents`** 用 env 一次性迁移。

## Goals / Non-Goals

**Goals:**

- 信封与运行时唯一备注字段：`events[].remark`（顶层展示/反查亦名 `remark`）
- create 成功落库后 `history.remark` 含专名（如菠菜）
- read / 备注反查 / 飞轮 payload 均读写 `remark`
- 运行时路径与分类提示词无字段名 `remark_keyword`
- 可选启动迁移：旧 payload 键 → `remark`，只动 Chroma

**Non-Goals:**

- 运行时 `remark or remark_keyword` 双读兼容
- 不改 Go 表结构；**不**回填 MySQL 已空的 `history.remark`
- 不做「从原句抠备注」规则引擎

## Decisions

1. **单字段名 `remark`**（create / read 共用，由 `op` 区分语义）
2. **权威在 `events[].remark`**；顶层 `remark` 可回填对齐
3. **提示词** 仅 `remark`
4. **落库** 只读 `remark`
5. **查史 / 反查 / 飞轮** 只读写 `remark`
6. **确认话术** create 有备注时附带「（备注…）」
7. **Chroma 一次性迁移**  
   - Env：`MIGRATE_INTENT_REMARK_KEYWORD_ON_STARTUP`（默认 false），对齐 `CLEAR_FEEDING_INTENTS_ON_STARTUP` 风格  
   - 时机：意图缓存预热初始化之后  
   - 规则：顶层与每条 `events[]`：若存在旧键且当前 `remark` 为空 → 赋给 `remark`；然后删除旧键；有非空 `remark` 则只删旧键不覆盖  
   - 与 clear：`clear=true` 时 **跳过** 迁移（清空优先）  
   - 旧键字面量 **仅** 允许出现在迁移实现内（读/删 JSON），不得进入运行时匹配/落库路径  
   - 日志：`migrated` / `touched` 计数 + 提醒改回 false  
8. **不迁 MySQL**

## Risks / Trade-offs

- [迁移代码含旧键字符串] → 限制在 store 迁移方法；任务验收用「除迁移外零匹配」或接受仅迁移文件出现。
- [clear 与 migrate 同开] → clear 优先，跳过迁移并打日志。
- [MySQL 空备注不恢复] → 产品已接受；仅修飞轮复现。

## Migration Plan

1. 部署含统一字段 + 迁移代码的版本，开关保持 false。  
2. 运维将 `MIGRATE_INTENT_REMARK_KEYWORD_ON_STARTUP=true`，重启一次，看日志。  
3. 改回 false。  
4. 回滚：无自动反向迁移；可依赖备份 Chroma 目录。

## Open Questions

- （无）
