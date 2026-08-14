## Context

`llm_client.invoke` 当前对可恢复错误按 `LLM_FALLBACK_MODELS` 串行换模；无 model 时整表当候选序。intent SSE 图内分类仍走 `invoke`，故会换模并拉长尾延迟。选型与 VIP 已在 Go；用户要求删除全部换模，无 model 直接挂，失败文案「脑电波过载，请稍后重试」。保留 Redis 闸门、HTTP 等非换模重试，不新增同模 LLM N 次重试。

## Goals / Non-Goals

**Goals:**

- `invoke` / `stream` 均只使用调用方传入的唯一合法 model；缺 model 立即失败。
- 废除保底候选构建与换模循环；清理 env/settings 保底列表。
- 意图分类（及同类已有软失败）用户文案统一为「脑电波过载，请稍后重试」；流式有 writer 时可再推一条 thinking。
- Python 不读 VIP；不按会员选模。

**Non-Goals:**

- 不在 Python 实现 VIP 策略。
- 不新增「同 model 自动再打 N 次」的 LLM 重试环。
- 不删除硅基/魔搭等 provider 接入（Go 仍可选型）。
- 不写测试文件。

## Decisions

### 1. 删除换模，保留闸门等非换模等待

- **选择**：去掉 `_build_candidate_configs` 保底段与 `invoke` 多候选循环；`invoke` 改为与 `stream` 类似的单次 `_invoke_once`。Redis `acquire` 自旋、兄弟仓 HTTP 重试、judge 业务默认配置保留。
- **理由**：用户明确「保留 Python 重试策略、仅删除换模」；现状 LLM 层并无同模 N 次重试。
- **备选**：失败后再同模重试 1～2 次 → 本期不做。

### 2. 无默认单模

- **选择**：`model_config` 为 None / provider 或 name 空 → `ValueError`（或等价），不读 `LLM_FALLBACK_MODELS`。
- **理由**：默认单模仍是 Python 选型；与「VIP/选型归 Go」冲突。
- **备选**：env 默认一个免费模 → 否决。

### 3. 契约：intent / care_alert model 必填（或省略即明确失败）

- **选择**：schema/注释改为必填或与 clinic 对齐；路由不再把空 dict 当作「走保底」。缺模在进入 LLM 前失败并映射用户文案。
- **理由**：与「无 model 直接挂」一致；Go 必须始终带模。

### 4. 失败文案与传播

- **选择**：共享常量或常量字符串 `脑电波过载，请稍后重试`。`classify_intent` 捕获 LLM 失败时：`content` 用该句；若在图流式上下文可 `emit_thinking` 同文。其它 `invoke` 调用点：能软回用户的对齐同句；只能上抛的由路由/HTTP 层映射（若已有）。
- **理由**：产品指定文案；先覆盖意图主路径，其它路径同口径尽量统一。

### 5. 配置清理

- **选择**：删除或废弃 `settings.llm_fallback_models` 与 env `LLM_FALLBACK_MODELS`；删除 `parse_llm_fallback_models` / `is_recoverable_llm_error`（若仅服务换模）。
- **理由**：避免运维误以为仍有保底。

### 6. VIP

- **选择**：代码与注释禁止 VIP 分支；规格保留「No VIP logic in Python」。
- **理由**：用户明确。

## Risks / Trade-offs

- [Go 仍省略 model] → 立即失败 + 脑电波文案；需同步 Go 发版。
- [上游瞬时 429] → 不再换家，用户需稍后重试（接受的权衡）。
- [care_alert / 澄清等未统一文案] → tasks 列出主路径必改，其余 invoke 点扫一遍对齐。

## Migration Plan

1. 部署 Python（无换模）前或同时：Go 保证 intent/care_alert 带 model。
2. 去掉 env 保底列表，避免误解。
3. 回滚：恢复 `llm-fallback-chain` 实现与 env（不推荐）。

## Open Questions

- 无（无 model 挂死、无同模 LLM 重试、文案已定）。
