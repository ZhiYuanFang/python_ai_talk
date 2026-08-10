## Why

护理留意（care_alert）当前依赖向量通识检索，并用 `suggestionId → knowledge_ids` 更新通识质量分。通识命中不稳定、飞轮与「提醒是否该出」耦合弱，且重启后无法沉淀「怎样提醒更好」的判定口径。需要改为**全局本地 prompt 飞轮**：反馈直接优化 prompt（对比样例摘要），经 Docker 挂载卷落盘，服务重启不丢；分析路径不再调知识库。

## What Changes

- care_alert **analyze 不再调用** `search_vectors` / 通识库；提示词去掉「相关知识摘录」依赖。
- **初始 / 运行中 prompt 从本地文件读取**（容器路径挂载卷，如 `/app/data/care_alert`）；文件不存在时用代码内默认模板 **bootstrap 并写出**。
- 默认模板组成：**输出格式** + **宝宝月龄占位** + **历史数据占位**；飞轮进化后额外增加 **用户反馈对比样例** 块。
- 月龄与近两日历史 **仅运行时注入**，禁止写入落盘 prompt；落盘模板必须保留动态占位符。
- **BREAKING（care_alert 飞轮语义）**：`POST /v1/care-alert/feedback` 不再对 `mother_baby_knowledge` 做质量加减分；改为写入全局反馈账本，并按阈值重写对比样例后原子写回本地 prompt。
- analyze 将 `suggestionId` 映射改为「本轮建议快照」（供反馈归因），不再映射 `knowledge_ids`。
- Docker compose / 部署约定增加 care_alert 数据目录 volume，与 chroma 卷并列，保证重启与换镜像不丢飞轮产物。
- 本变更 **取代** 既有 change `care-alert-knowledge-flywheel` 中 care_alert「通识质量飞轮」方向（clinic 等其它通识飞轮不受影响）。

## Capabilities

### New Capabilities

- `care-alert-prompt-flywheel`: 全局本地 prompt 加载/bootstrap、动态槽渲染、无知识库 analyze、固定意图反馈 → 对比样例摘要飞轮、长度上限与落盘持久化

### Modified Capabilities

- `docker-deployment`: 基线 compose 增加 care_alert 提示词/账本数据目录的 volume 挂载约定（与 chroma 卷策略并列）
- `env-config`: 增加 care_alert prompt 目录等可配置项（默认指向挂载路径）

## Impact

- **代码**：`app/care_alert/**`（图去掉 `search_vectors`、prompt 组装、flywheel_store 语义、analyze/feedback 路由与服务）、`app/config/settings.py`、`docker-compose.yml`（及部署文档若需同步 volume 说明）
- **API**：`POST /v1/care-alert/analyze` 与 `/feedback` 请求/响应外形可保持；feedback **副作用**从通识质量分改为 prompt 飞轮（Go 仍可 best-effort 调用）
- **存储**：新增 Docker bind/volume（如 `./data/care_alert → /app/data/care_alert`）；Redis 映射 value 从 knowledge_ids 改为建议快照（或等价本地/Redis TTL 存储）
- **非目标**：不改 clinic/tip 通识飞轮；不做 per-device prompt；不强制 Go/Flutter 改字段枚举（仍 `ignore|follow_up`）
