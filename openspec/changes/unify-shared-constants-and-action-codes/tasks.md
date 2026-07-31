## 1. Shared constants

- [x] 1.1 新建 `app/shared/constants.py`，定义英文枚举：`IntentAction`、`TargetType`、`MatchSource`、`VectorSource`、`ConfirmType`、`ResolveStatus`、`ResolveOp`（及代码所需的 `EventType` 等）；文件内无中文 label
- [x] 1.2 从 `clarification.py` 迁入或 re-export `ResolveStatus`，避免双定义漂移

## 2. Vector write path

- [x] 2.1 修改 `event_vector_store`：标准变体 `metadata.action` 与 id 使用英文 IntentAction；document 中文语料用模块内私有映射拼接（不进 constants）
- [x] 2.2 修改 `add_user_expression` 及相关调用：写入英文 action（空则按约定默认）
- [x] 2.3 修改 `match_event_by_vector`：直接使用 `metadata.action` 或默认 `IntentAction.ONE`；**不做**中文读兼容
- [x] 2.4 更新 `docs/vector_db_guide.md` 中 metadata.action 示例为英文

## 3. Pending response action semantics

- [x] 3.1 修改 `pending_to_response_fields`：顶层 `action` 使用 `pending.action`，移除 `disambiguate`
- [x] 3.2 梳理 `intent_pipeline` / `clarification` / 图节点 / 路由中 IntentAction、TargetType、MatchSource、ConfirmType 硬编码，改为引用 constants
- [x] 3.3 内部澄清操作改用 `ResolveOp`（字段重命名可选；至少常量引用 + 注释标明非 IntentResponse.action）

## 4. ENV-gated standard rebuild

- [x] 4.1 在 `settings` 增加 `rebuild_feeding_standard_events: bool = False`，对应环境变量 `REBUILD_FEEDING_STANDARD_EVENTS`
- [x] 4.2 修改启动预热：开关为 true 时先成功获取叶子事件字典，再 `initialize_events`；字典失败则不删库并打错误日志
- [x] 4.3 更新 `.env.example` / `env/.env.local|.test|.prod` / `docker-compose.yml` 注释与 `docs/deploy-guide.md`：说明一次性重建用法与默认 false

## 5. Tests and verification

- [x] 5.1 单测：标准变体写入 metadata/id 为英文；document 可为中文表面语料
- [x] 5.2 单测：pending 响应 `need_confirm=true` 且 `action` 为 pending 喂养动作而非 `disambiguate`
- [x] 5.3 单测或文档化：rebuild 开关 false 时不强制全量重建；true 且字典失败时不删除 standard
