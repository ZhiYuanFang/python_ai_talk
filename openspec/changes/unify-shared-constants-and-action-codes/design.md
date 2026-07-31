## Context

意图分析对外契约要求 `IntentResponse.action` 为英文协议值（`start|end|one|search|suggestion|reply|exit|multi` 等），澄清态由 `need_confirm` / `confirm_type` 表达。

当前问题：

1. `EventVectorStore.STANDARD_ACTIONS = ["开始","结束","记录"]` 写入路径仍会把中文写入 metadata（即使现网库已整理干净，新写入仍会污染）
2. `pending_to_response_fields` 固定 `action="disambiguate"`，与 schema/文档及 Go 侧「以 need_confirm 为闸门」不一致
3. 协议字符串散落硬编码；`ResolveResult.action`（confirm/select/…）与意图 `action` 同名不同域，易混淆
4. 启动预热在 `event_count > 0` 时跳过 `initialize_events`；普通 sync 不重写未改名事件（ENV 重建作为可选运维手段保留）

**前提**：向量库存量已整理为英文 `metadata.action` / id，本 change **不做**读路径中文→英文兼容。

## Goals / Non-Goals

**Goals:**

- 在 `app/shared/constants.py` 统一定义英文协议枚举，保证输出格式一致
- 向量 / 飞轮 / IntentResponse 的动作字段一律使用 IntentAction 真值入库与出站
- 去掉对外 `disambiguate`；澄清态只靠 `need_confirm` + `confirm_type`
- 通过 ENV 可选一次性重建 standard 向量；保留 user 飞轮

**Non-Goals:**

- 不把日志文案、LLM prompt、用户可见整句抽进 constants
- constants 中不放中文 label
- **不做** metadata 读路径对遗留中文 action 的归一化（库已整理）
- 不强制批量改写 `user_*` 的 document / embedding
- 不自动检测旧中文并重建（仅 ENV 显式触发）
- 不改变 Go/Flutter 以 `need_confirm` 分支的主路径

## Decisions

### 决策 1：constants 放在 `app/shared/constants.py`，纯英文枚举

- **选择**：`str, Enum`（或等价常量类）按域拆分：`IntentAction`、`TargetType`、`MatchSource`、`VectorSource`、`ConfirmType`、`ResolveStatus`、`ResolveOp`、`EventType`（若代码有引用）等
- **理由**：跨 feeding/clinic 共用；与「保证输出格式」目标一致；无中文避免把展示语当成协议值
- **替代**：放 `app/feeding/constants.py` —— 否决（用户指定 shared）；单一巨型 `Action` 枚举 —— 否决（意图动作与澄清操作同名冲突）

### 决策 2：对外 `action` 只承载 IntentAction；去掉 `disambiguate`

- **选择**：`pending_to_response_fields` 使用 `pending.action`（默认 `one`）；`need_confirm=true`；`confirm_type=pending.kind`
- **理由**：与 deploy-guide 示例（`action=start` + `need_confirm=true`）及 Go 闸门一致；同字段同含义
- **替代**：把 `disambiguate` 升格进 IntentAction —— 否决（字段兼状态）

### 决策 3：内部澄清操作使用 `ResolveOp`，不写入 IntentResponse.action

- **选择**：`ResolveResult` 使用 `resolve_op`（或保留字段但取值来自 `ResolveOp`），与 `IntentAction` 分离
- **理由**：confirm/select/correct 仅管线内部；成功落叶子时对外仍用 `pending.action`

### 决策 4：向量写入 — metadata 英文，document 中文语料本地拼接

- **选择**：`metadata.action` / 变体 id 使用 `start|end|one`；`document` 仍可为「开始{事件名}」等，中文前缀定义在 `event_vector_store`（或邻接私有映射），**不进** constants
- **映射**（仅写入侧 document 语料）：start→开始，end→结束，one→记录
- **理由**：embedding 需中文语料；协议字段必须英文

### 决策 5：不做 metadata 读兼容

- **选择**：`match_event_by_vector` 直接使用 `metadata.action`（空则默认 `IntentAction.ONE`）；不把「开始/结束/记录」映射为英文
- **理由**：存量向量库已整理；减少无用分支
- **替代**：读路径短期归一化 —— 否决（用户确认不需要）

### 决策 6：存量 — ENV 一次性重建 standard（可选运维）

- **选择**：`REBUILD_FEEDING_STANDARD_EVENTS`（settings：`rebuild_feeding_standard_events: bool = False`）
- **安全序**：先成功获取叶子事件字典，再调用 `initialize_events`（内部删 standard 后重写）；字典失败则**不删库**
- **默认 false**；按需临时 true 重启一次，完成后改回 false
- **理由**：库已整理后非必做，但保留开关便于环境对齐/再初始化；复用现有 `initialize_events`
- **替代**：启动自动检测中文 —— 否决；只 upsert 新 id 不删旧 —— 否决

### 决策 7：与 event_cache 首次 initialize 的关系

- **选择**：接受可能双跑（启动 rebuild + cache 首次 `initialize_events`），二者幂等
- **替代**：rebuild 后预填 `_previous_dictionary` 跳过 —— 可后续优化，首版不做

## Risks / Trade-offs

- [若某环境仍残留中文 metadata] → 出站可能再次出现中文 action；依赖运维已整理或开启 ENV 重建对齐
- [多副本并发 rebuild 同一 volume] → 发版时单实例或串行开启 ENV；文档说明
- [重建窗口 standard 暂时为空/不全] → 短窗口；匹配可能降级 LLM；选低峰操作
- [客户端依赖 `action=disambiguate`] → 仓库内无引用；文档已强调 need_confirm；列为 BREAKING 并沟通
- [initialize 先删后写] → 调用方必须先拿到字典；ENV 路径禁止在拉取失败时删除

## Migration Plan

1. 合并代码（写路径英文 + 去 disambiguate + ENV 开关默认 false；无读兼容）
2. （可选）若某环境未整理干净：设 `REBUILD_FEEDING_STANDARD_EVENTS=true`，重启，确认日志后改回 false
3. 验证向量匹配返回英文 `action`；pending 返回原喂养 action + `need_confirm=true`

**Rollback：** 关闭 rebuild ENV；避免在已按新格式写入的库上直接回退旧写路径而无重建。

## Open Questions

- 无阻塞项。`ResolveResult` 字段是重命名为 `resolve_op` 还是仅改取值来源：实现时优先最小改动（常量引用 + 注释），重命名若触达面大可列为同 change 内可选。
