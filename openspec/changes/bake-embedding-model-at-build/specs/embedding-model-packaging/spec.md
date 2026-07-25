## ADDED Requirements

### Requirement: Embedding 模型在镜像构建时下载并打入镜像
Docker 镜像构建流程 SHALL 在构建阶段下载配置的 Embedding 模型（默认 `BAAI/bge-small-zh-v1.5`）并写入镜像内固定目录（`/app/data/models`），不得依赖容器首次启动时从 HuggingFace Hub 下载。

#### Scenario: 构建产物包含模型缓存
- **WHEN** 完整执行应用 Dockerfile 构建
- **THEN** 最终镜像中存在 `/app/data/models` 下的模型缓存文件
- **AND** 构建阶段已执行预下载步骤（例如通过 SentenceTransformer 写入 cache_folder）

#### Scenario: 模型不进入 Git
- **WHEN** 查看版本控制忽略规则
- **THEN** `data/models/` SHALL 被 gitignore（模型不作为源码提交）

### Requirement: 运行时离线加载 Embedding 模型
应用在容器内加载 Embedding 模型时 SHALL 仅使用本地缓存，不得因缺少或检查更新而访问 HuggingFace Hub。

#### Scenario: 加载使用 local_files_only
- **WHEN** 知识向量库或喂养事件向量库初始化 Embedding
- **THEN** SentenceTransformer（或等价加载路径）以仅本地文件模式加载
- **AND** 使用与镜像内一致的缓存目录（`data/models`）

#### Scenario: 运行时环境变量强制离线
- **WHEN** 查看应用 runtime 镜像环境变量
- **THEN** 存在禁止 Hub 访问的配置（例如 `HF_HUB_OFFLINE=1` 与 `TRANSFORMERS_OFFLINE=1`）

### Requirement: Compose 不得用空目录覆盖镜像内模型
`docker-compose` 基线配置 SHALL NOT 将宿主机 `data/models`（或等价空目录）bind-mount 到容器内模型缓存路径；Chroma 持久化目录的 volume 策略保持独立。

#### Scenario: 无 models volume 覆盖
- **WHEN** 查看基线 `docker-compose.yml` 的 volumes
- **THEN** 不存在将宿主机 models 目录挂载到容器 `/app/data/models` 的条目
- **AND** `chroma_db` 持久化挂载仍可保留

#### Scenario: 启动不访问 HuggingFace
- **WHEN** 使用不含 models bind-mount 的 compose 启动已构建镜像，且运行环境无法访问 huggingface.co
- **THEN** Embedding 初始化仍能成功完成
- **AND** 服务健康检查可通过
