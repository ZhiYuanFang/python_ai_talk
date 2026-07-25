## Context

项目使用 `BAAI/bge-small-zh-v1.5` 做向量 Embedding。`data/models/` 已在 `.gitignore` / `.dockerignore` 中排除，不进入 Git。Dockerfile 已有「builder 阶段 SentenceTransformer 预下载 → runtime `COPY`」逻辑，意图是避免容器启动时访问 HuggingFace。

实际故障路径：`docker-compose.yml` 将宿主机空的 `./data/models` bind-mount 到 `/app/data/models`，覆盖镜像内已下载文件；运行时 `SentenceTransformer` 仍尝试 HEAD `huggingface.co`，在无外网环境失败。

已确认产品决策：**构建时下载模型**（非运行时下载）。部分防护改动可能已在工作区落地，本 change 将其固化为需求与验收标准，并补齐文档与残留缺口。

## Goals / Non-Goals

**Goals:**

- 模型仅在 `docker build` 阶段获取并打入镜像
- 运行时只使用镜像内本地缓存，不访问 HuggingFace Hub
- compose 不覆盖 `/app/data/models`
- 文档与实现一致

**Non-Goals:**

- 不改为运行时首次下载
- 不把模型提交进 Git
- 不更换 Embedding 模型或向量维度
- 不解决构建机无法访问 HF 的网络问题本身（可另开「构建期镜像源」change）；本设计假设构建环境可下载或已配置 endpoint
- 不改变 `chroma_db` 的 volume 持久化策略

## Decisions

### D1: 构建时预下载，禁止运行时下载

**决定**：保留/强化 Dockerfile builder 中的预下载；runtime 设置 `HF_HUB_OFFLINE=1`、`TRANSFORMERS_OFFLINE=1`，代码侧 `local_files_only=True`。

**备选**：容器启动时下载 → 否决（运行环境常无法访问 HF；与已发生故障一致）。

### D2: 不挂载 `data/models` volume

**决定**：compose 只挂 `chroma_db`；`models` 留在镜像层。注释明确禁止空目录挂载。

**备选**：挂载 volume 且要求宿主机预置模型 → 否决（与「构建自动下载、不进 Git」冲突，易再次踩空目录覆盖）。

### D3: 缓存路径统一为 `/app/data/models`

**决定**：builder `cache_folder='data/models'`，runtime `SENTENCE_TRANSFORMERS_HOME=/app/data/models`，应用 `cache_folder=os.path.join("data", "models")` 与之一致；`COPY` 放在 `COPY . .` 之后避免被空目录覆盖。

### D4: 文档写清「构建打入 / 运行离线」

**决定**：更新 deploy / vector_db 说明：本地 `mkdir data/models` 仅适用于非 Docker 的 poetry 开发路径；Docker 路径依赖镜像内模型。

## Risks / Trade-offs

- [构建机无法访问 HF，build 失败] → 构建日志可见；临时在 builder 配置 `HF_ENDPOINT` 镜像源（本 change 可加注释预留，不强制实现）
- [镜像体积 +~90MB] → 可接受；换运行时下载会更脆
- [兄弟仓 compose 仍挂载 models] → 检查 go_ai_talk 侧 python-ai-talk 服务段；若有则同步去掉
- [已运行容器仍带旧 volume] → 迁移时需 `down` 再 `up`，去掉旧 mount

## Migration Plan

1. 确保 Dockerfile / compose / 加载代码符合本设计（含核对已有未提交改动）
2. 重建镜像并启动（无 models bind-mount）
3. 确认日志无对 `huggingface.co` 的重试，Embedding 初始化成功，health 通过
4. 回滚：恢复旧 compose 挂载仅在宿主机已有完整模型缓存时可行；否则回滚会导致再次外网下载

## Open Questions

- （无）构建时下载策略已在 explore 中确认
