## ADDED Requirements

### Requirement: Dockerfile
系统 SHALL 提供 Dockerfile，支持多阶段构建，生成轻量级生产镜像。

#### Scenario: 构建开发镜像
- **WHEN** 执行 `docker build -t python-ai-talk:dev .`
- **THEN** 构建包含所有依赖的开发镜像

#### Scenario: 构建生产镜像
- **WHEN** 执行 `docker build --target=production -t python-ai-talk:prod .`
- **THEN** 构建轻量级生产镜像，仅包含运行时依赖

#### Scenario: 镜像体积优化
- **WHEN** 构建生产镜像
- **THEN** 镜像体积不超过 1GB

### Requirement: Docker Compose 配置
系统 SHALL 在 go_ai_talk 的 docker-compose.microservices.yml 中新增 python-ai-talk 服务配置。

#### Scenario: 本地开发环境
- **WHEN** 在 go_ai_talk 目录执行 `docker-compose -f manifest/docker/docker-compose.microservices.yml up`
- **THEN** python-ai-talk 服务启动，并加入 go-ai-talk-net 网络

#### Scenario: 服务依赖
- **WHEN** docker-compose 启动
- **THEN** python-ai-talk 服务在 history-service 和 device-service 启动后启动

#### Scenario: 环境变量注入
- **WHEN** docker-compose 启动
- **THEN** python-ai-talk 服务从环境变量获取配置（DEEPSEEK_API_KEY, REDIS_URL 等）

#### Scenario: Volume 挂载
- **WHEN** docker-compose 启动
- **THEN** chroma-data 和 embedding-models Volumes 被挂载到容器

### Requirement: 生产环境配置
系统 SHALL 在 docker-compose.microservices.prod.yml 中新增 python-ai-talk 服务的生产配置。

#### Scenario: 生产镜像
- **WHEN** 启动生产环境
- **THEN** python-ai-talk 使用 `${REGISTRY}/python-ai-talk:${IMAGE_TAG}` 镜像

#### Scenario: 生产网络
- **WHEN** 启动生产环境
- **THEN** python-ai-talk 加入 go-ai-talk-net 外部网络

### Requirement: 健康检查
系统 SHALL 提供健康检查接口 `/health`，支持 Docker healthcheck。

#### Scenario: 健康检查成功
- **WHEN** Docker 执行 healthcheck
- **THEN** `/health` 接口返回 HTTP 200

#### Scenario: 健康检查失败
- **WHEN** 服务异常
- **THEN** `/health` 接口返回非 200 状态码

### Requirement: 向量库运行时构建
系统 SHALL 在服务启动时检测向量库是否存在，不存在则自动构建。

#### Scenario: 首次启动自动构建
- **WHEN** 服务首次启动且 Chroma 数据目录为空
- **THEN** 服务自动执行向量库构建脚本

#### Scenario: 已存在向量库跳过构建
- **WHEN** 服务启动且 Chroma 数据目录已存在数据
- **THEN** 服务跳过向量库构建，直接加载现有数据