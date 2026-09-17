## Why

护理留意 prompt 飞轮、clinic Q&A 捷径飞轮、通识知识质量飞轮及通识检索注入，与「提醒/回答是否更好」耦合弱或未兑现收益，却拉高图节点、会话字段、Chroma 集合与定时清理复杂度。产品确认仅保留喂养**意图缓存飞轮**（确认落库后缓存整句 CRUD，使意图识别越来越快）；其余飞轮与通识参考链路应删除以减负。

## What Changes

- **保留**：`feeding_intents` 意图缓存飞轮（匹配、确认后写入、质量分与定时清理）；MUST NOT 误删或改坏该路径。
- **删除 care_alert 飞轮**：去掉 ledger / 对比样例重写 / Redis suggestion 快照飞轮；analyze 仅用静态 prompt（`prompt.json` 的 `output_format` 或等价内联）；**BREAKING** 删除 `POST /v1/care-alert/feedback`。
- **删除 Q&A 飞轮与捷径**：去掉 clinic 的 rewrite / search_qa / format 捷径链、`qa_fast_path` 集合读写与质量升降。
- **删除通识飞轮与参考逻辑**：clinic/tip 不再 `search_vectors`、不再向 prompt 注入「知识库参考」；删除通识质量加减分与低质量清理；**BREAKING** 删除 `/v1/knowledge/*`。
- **删除 clinic `implicit_feedback` 节点**：去 Q&A/通识后该节点无事可做，从图入口移除，并删除 `suggestion_acceptance` 中飞轮副作用。
- **归档删除**：`data/knowledge/**` 通识 MD 语料、`scripts/build_vector_db.py`（及启动时自动建通识库逻辑）；相关文档口径同步收缩。
- 跨仓：**BREAKING** Go 须停调已删端点（Flutter 相关业务线视为已下线）；本仓不改 Go/Flutter 源码。

## Capabilities

### New Capabilities

- `intent-cache-flywheel`: 明确喂养意图缓存为仓库唯一保留的数据飞轮（匹配、写入、清理边界）
- `care-alert-static-prompt`: care_alert 仅静态 prompt 分析；无 feedback 飞轮端点

### Modified Capabilities

- `knowledge-flywheel`: 退役通识质量飞轮与相关清理/排序要求
- `knowledge-management-api`: 退役 `/v1/knowledge` 管理 API
- `knowledge-quality-hard-filter`: 退役通识检索质量硬过滤（随检索删除）
- `qa-fast-path`: 退役全局 Q&A 捷径与 promote/demote
- `implicit-suggestion-feedback`: 退役隐式三态判定及一切飞轮副作用
- `retire-explicit-feedback`: 不再要求「隐式采纳驱动通识质量」；与隐式路径一并退役
- `vector-db-build`: 退役通识 MD → `mother_baby_knowledge` 构建脚本与启动 bootstrap
- `shared-graph-nodes`: clinic/tip MUST NOT 依赖 `search_vectors` 注入通识
- `companion-session`: 去掉为通识/Q&A 飞轮服务的 `last_suggestion` 字段约定
- `langgraph-clinic-graph`: 入口与路由不再含 implicit_feedback / Q&A / search_vectors
- `tip-generation`: tip 路径不再检索或注入通识知识
- `env-config` / `docker-deployment`: 收缩 care_alert 飞轮卷与通识构建相关配置说明（保留静态 prompt 目录若仍需要）

## Impact

- **代码**：`app/care_alert/**`（flywheel_*、feedback 路由）、`app/clinic/**`、`app/tip/**`、`app/shared/suggestion_acceptance.py`、`qa_fast_path.py`、`search_vectors` 调用点、`vector_store` 通识/Q&A API、`app/api/routes/knowledge.py`、`main.py` 清理与 bootstrap、`scripts/build_vector_db.py`、`data/knowledge/**`
- **API**：**BREAKING** 移除 `POST /v1/care-alert/feedback`、`/v1/knowledge/*`；`/v1/care-alert/analyze` 保留
- **存储**：不再维护 `mother_baby_knowledge`、`qa_fast_path`；**保留** `feeding_intents`
- **非目标**：不改意图 CRUD 主语义（除确保缓存飞轮完好）；不改 growth_trajectory；不在本仓修改 Go/Flutter
