## Why

Embedding 模型 `BAAI/bge-small-zh-v1.5` 不进 Git（`data/models/` 已 ignore），但运行时若依赖 HuggingFace 下载，在国内/隔离网络下会 `Network is unreachable` 导致服务不可用。策略应明确为：**构建镜像时下载并打进镜像层**，运行时只读本地缓存、不访问 Hub。此前 compose 挂载宿主机空的 `./data/models` 会覆盖镜像内模型，使构建预下载失效。

## What Changes

- 固化「构建时预下载 Embedding 模型 → 复制进 runtime 镜像」的 Dockerfile 约定
- **BREAKING**（部署侧）：`docker-compose` **不得**将宿主机空目录挂载到容器 `/app/data/models`（仅保留 `chroma_db` 等需持久化的 volume）
- 运行时加载 SentenceTransformer 使用本地缓存（`local_files_only`），并设置 `HF_HUB_OFFLINE` / `TRANSFORMERS_OFFLINE` 等环境变量，禁止启动期访问 Hub
- 同步部署/向量库文档中关于模型获取方式的说明（构建打入镜像，而非运行时下载或 Git 提交）

## Capabilities

### New Capabilities

- `embedding-model-packaging`: 约定 Embedding 模型的获取时机（构建时）、镜像内路径、运行时离线加载，以及 compose volume 约束

### Modified Capabilities

- （无）`openspec/specs/` 下暂无已归档能力需改需求

## Impact

- **Dockerfile**：builder 预下载、`COPY` 到 `/app/data/models`、runtime `ENV` 离线
- **docker-compose.yml**：移除或禁止 `data/models` 挂载
- **应用代码**：`vector_store` / `event_vector_store` 加载参数
- **文档**：`docs/deploy-guide.md`、`docs/vector_db_guide.md` 等
- **不受影响**：HTTP API、Chroma 集合 schema、业务图逻辑；`chroma_db` volume 策略不变
- **构建依赖**：构建机须能访问 HuggingFace（或配置的镜像源）；模型约 +90MB 镜像体积
