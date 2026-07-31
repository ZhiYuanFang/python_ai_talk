## Why

喂养意图链路中协议枚举值（尤其是 `action`）散落硬编码，且标准向量写入把中文「开始/结束/记录」存进 metadata，导致向量匹配返回 `action=开始`，与 API 契约（`start|end|one|…`）不一致。同时 pending 澄清响应用 `action=disambiguate` 占用动作字段，与 `need_confirm` 职责重叠，破坏「同一返回字段含义相同」。

## What Changes

- 新增 `app/shared/constants.py`：统一定义英文协议枚举（IntentAction、TargetType、MatchSource、VectorSource、ConfirmType、ResolveStatus/ResolveOp 等）；**不含中文 label**
- 业务代码拒绝硬编码上述枚举字符串，改引用 constants
- 向量库 / 飞轮写入：`metadata.action`（及 standard 变体 id）直接存英文枚举值；embedding `document` 所需中文语料不进 constants，留在写入侧本地拼接
- **BREAKING（对外语义收紧）**：pending 澄清响应不再返回 `action=disambiguate`；改为返回 `pending.action`（喂养动作），以 `need_confirm` + `confirm_type` 表达澄清态
- 存量：向量库已人工整理为英文 action，**不做** metadata 读路径中文兼容；仍保留环境变量一次性重建 `source=standard`（默认关闭）作为可选运维手段，重建时保留 `user_*`

## Capabilities

### New Capabilities

- `shared-protocol-constants`: 共享英文协议枚举定义与代码引用约束；保证 IntentResponse / 向量 metadata 等输出格式一致
- `feeding-action-storage`: 喂养事件向量与飞轮的 action 存取规范（英文枚举直存、document 语料分离、ENV 可选重建）

### Modified Capabilities

- （无已归档主规格需 delta；澄清态 action 行为作为新规格场景覆盖）

## Impact

- 代码：`app/shared/constants.py`（新建）、`event_vector_store`、`match_event_by_vector`、`clarification` / `intent_pipeline`、意图图节点与路由、`settings` / 启动预热、相关测试与部署文档
- API：`IntentResponse.action` 在 `need_confirm=true` 时不再出现 `disambiguate`（依赖 `need_confirm` 的 Go/客户端不受影响；若有客户端误依赖 `disambiguate` 需同步）
- 运维：新增 `REBUILD_FEEDING_STANDARD_EVENTS`（默认 `false`）；发版后按需开启一次以重建 standard 向量
- 数据：重建仅删除并重写 `source=standard`；用户飞轮表达保留
