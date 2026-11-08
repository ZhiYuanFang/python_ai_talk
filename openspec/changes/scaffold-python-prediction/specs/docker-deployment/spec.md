## ADDED Requirements

### Requirement: 双服务 Compose 基线
本仓基线 `docker-compose.yml` SHALL 同时定义 `python-ai-talk` 与 `python-prediction` 两个服务骨架（build、healthcheck、必要 environment 占位）。基线 MUST NOT 为两服务声明宿主机 `ports`（ports 由 local/test/prod overlay 提供，避免合并叠加）。

#### Scenario: 基线含两服务
- **WHEN** 运维查看基线 `docker-compose.yml`
- **THEN** 存在 service 键 `python-ai-talk` 与 `python-prediction`
- **AND** 两服务均无宿主机 ports 映射

### Requirement: python-prediction 镜像与 overlay 端口
local overlay SHALL 将 `python-prediction` 映射为本地镜像 `go-ai-talk/python-prediction:local`，宿主机端口 `8001:8001`，并加入外部网络 `go-ai-talk-net`。test overlay SHALL 使用 `${REGISTRY}/python-prediction:${IMAGE_TAG}`，宿主机端口 `18001:8001`，网络 `go-ai-talk-test-net`。prod overlay SHALL 使用 `${REGISTRY}/python-prediction:${IMAGE_TAG}`，宿主机端口 `8001:8001`，网络 `go-ai-talk-net`。

#### Scenario: 本地端口
- **WHEN** 使用 local overlay 启动
- **THEN** 宿主机可经 `8001` 访问 prediction 健康检查

#### Scenario: 测试端口
- **WHEN** 使用 test overlay 启动
- **THEN** 宿主机可经 `18001` 访问 prediction（容器内 8001）

#### Scenario: 生产镜像名
- **WHEN** 使用 prod overlay 启动
- **THEN** prediction 的 image 为 `${REGISTRY}/python-prediction:${IMAGE_TAG}`

### Requirement: talk Dockerfile 文件名
python-ai-talk 的生产镜像构建文件 SHALL 为仓库根目录 `Dockerfile.python-ai-talk`。Compose build 段与 CI MUST 引用该路径（不再以未加服务后缀的 `Dockerfile` 作为权威构建文件）。

#### Scenario: compose 指向 talk Dockerfile
- **WHEN** 查看基线中 `python-ai-talk` 的 build.dockerfile
- **THEN** 值为 `Dockerfile.python-ai-talk`

### Requirement: prediction Dockerfile
系统 SHALL 提供 `Dockerfile.python-prediction`，用于构建可运行健康检查骨架的轻量镜像；该镜像 MUST NOT 为满足本变更而安装与 talk 相同的 torch / chromadb / sentence-transformers 重依赖。

#### Scenario: 轻量构建文件存在
- **WHEN** 执行 `docker build -f Dockerfile.python-prediction -t python-prediction:local .`
- **THEN** 构建成功且容器内健康检查可通过

### Requirement: 可选预留 PYTHON_PREDICTION_URL
基线或 `.env.example` MAY 为 `python-ai-talk` 预留环境变量 `PYTHON_PREDICTION_URL`（默认同网地址 `http://python-prediction:8001`）。本变更 MUST NOT 要求 talk 应用代码必须读取或调用该 URL。

#### Scenario: 文档或 env 模板出现预留
- **WHEN** 检查 `.env.example` 或基线 environment
- **THEN** 可见 `PYTHON_PREDICTION_URL` 占位或其文档说明
- **AND** 现有意图预测行为不因该预留而改变

## MODIFIED Requirements

### Requirement: Dockerfile
系统 SHALL 分别为 `python-ai-talk` 与 `python-prediction` 提供 Dockerfile（`Dockerfile.python-ai-talk`、`Dockerfile.python-prediction`）。`python-ai-talk` 镜像可继续使用多阶段构建以容纳其运行时依赖；`python-prediction` 在本变更内 SHALL 为轻量运行时镜像。

#### Scenario: 构建 talk 镜像
- **WHEN** 执行 `docker build -f Dockerfile.python-ai-talk -t python-ai-talk:local .`
- **THEN** 构建得到可运行的 python-ai-talk 镜像

#### Scenario: 构建 prediction 镜像
- **WHEN** 执行 `docker build -f Dockerfile.python-prediction -t python-prediction:local .`
- **THEN** 构建得到可运行的 python-prediction 轻量镜像
