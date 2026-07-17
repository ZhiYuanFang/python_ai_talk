# Spec: 部署指南文档 (deploy-guide)

## ADDED Requirements

### Requirement: 提供完整的目录结构说明

文档 SHALL 包含项目部署相关文件的完整目录结构图，帮助新手快速定位配置文件。

#### Scenario: 新手查看目录结构
- **WHEN** 新手打开部署指南文档
- **THEN** 文档 SHALL 展示以下目录结构：
  ```
  python_ai_talk/
  ├── docker-compose.yml          # 基线配置（定义服务骨架）
  ├── docker-compose.local.yml    # 本地开发 overlay
  ├── docker-compose.test.yml     # 测试环境 overlay
  ├── docker-compose.prod.yml     # 生产环境 overlay
  └── env/
      ├── .env.example            # 环境变量模板（提交到 Git）
      ├── .env.local              # 本地开发环境变量（不提交）
      ├── .env.test               # 测试环境变量（不提交）
      └── .env.prod               # 生产环境变量（不提交）
  ```

### Requirement: 提供本地开发环境部署指南

文档 SHALL 包含本地开发环境的完整部署步骤，从环境准备到服务启动。

#### Scenario: 本地开发环境从零开始部署
- **WHEN** 新手在本地机器上部署开发环境
- **THEN** 文档 SHALL 提供以下步骤：
  1. 环境准备（安装 Docker、Docker Compose）
  2. 克隆代码仓库
  3. 复制环境变量模板并填写必要配置
  4. 构建向量数据库（首次运行）
  5. 启动服务命令
  6. 验证服务健康状态

#### Scenario: 本地开发环境启动命令
- **WHEN** 新手执行本地开发环境启动
- **THEN** 文档 SHALL 提供可复制的完整命令：
  ```bash
  docker compose --env-file env/.env.local \
    -f docker-compose.yml \
    -f docker-compose.local.yml \
    up -d --build
  ```

### Requirement: 提供测试环境部署指南

文档 SHALL 包含测试环境的完整部署步骤，包括镜像拉取、环境变量配置、服务启动。

#### Scenario: 测试环境从零开始部署
- **WHEN** 运维人员在 Linux 服务器上部署测试环境
- **THEN** 文档 SHALL 提供以下步骤：
  1. 环境准备（安装 Docker、Docker Compose、创建网络）
  2. 登录 ACR 镜像仓库
  3. 创建环境变量文件 `.env.test`
  4. 拉取指定版本镜像
  5. 启动服务命令
  6. 验证服务健康状态

#### Scenario: 测试环境启动命令
- **WHEN** 运维人员执行测试环境启动
- **THEN** 文档 SHALL 提供可复制的完整命令：
  ```bash
  docker compose --env-file env/.env.test \
    -f docker-compose.yml \
    -f docker-compose.test.yml \
    pull && up -d --no-build
  ```

### Requirement: 提供生产环境部署指南

文档 SHALL 包含生产环境的完整部署步骤，强调安全性和回滚策略。

#### Scenario: 生产环境从零开始部署
- **WHEN** 运维人员在生产服务器上部署服务
- **THEN** 文档 SHALL 提供以下步骤：
  1. 环境准备（安装 Docker、Docker Compose、创建网络）
  2. 登录 ACR 镜像仓库
  3. 创建环境变量文件 `.env.prod`（注意密钥安全）
  4. 拉取指定版本镜像
  5. 启动服务命令
  6. 验证服务健康状态
  7. 回滚操作说明

#### Scenario: 生产环境启动命令
- **WHEN** 运维人员执行生产环境启动
- **THEN** 文档 SHALL 提供可复制的完整命令：
  ```bash
  docker compose --env-file env/.env.prod \
    -f docker-compose.yml \
    -f docker-compose.prod.yml \
    pull && up -d --no-build
  ```

### Requirement: 提供环境变量配置说明

文档 SHALL 包含所有环境变量的详细说明，包括变量名、用途、示例值、默认值。

#### Scenario: 环境变量清单查阅
- **WHEN** 新手需要配置环境变量
- **THEN** 文档 SHALL 提供环境变量清单表格，包含：
  | 变量名 | 用途 | 示例值 | 必填 |
  |--------|------|--------|------|
  | REGISTRY | ACR 仓库地址 | crpi-xxx.../pangbao-test | 是 |
  | IMAGE_TAG | 镜像版本号 | v2.0.7-beta.43 | 是 |
  | PYTHON_AI_TALK_DEEPSEEK_API_KEY | DeepSeek API 密钥 | sk-xxx | 是 |
  | PYTHON_AI_TALK_GLM_API_KEY | 智谱 GLM API 密钥 | xxx | 是 |
  | PYTHON_AI_TALK_REDIS_URL | Redis 连接地址 | redis://localhost:6379/0 | 是 |
  | PYTHON_AI_TALK_HISTORY_SERVICE_URL | history-service 地址 | http://history-service:9801 | 是 |
  | PYTHON_AI_TALK_DEVICE_SERVICE_URL | device-service 地址 | http://device-service:9803 | 是 |
  | PYTHON_AI_TALK_VOICE_SERVICE_URL | voice-service 地址 | http://voice-service:9802 | 是 |
  | PYTHON_AI_TALK_CHROMA_PERSIST_DIR | 向量库存储路径 | /app/data/chroma_db | 否 |
  | PYTHON_AI_TALK_EMBEDDING_MODEL | Embedding 模型名称 | BAAI/bge-small-zh-v1.5 | 否 |

### Requirement: 提供常见问题解答

文档 SHALL 包含部署过程中常见问题的解答，帮助新手自助排查问题。

#### Scenario: 服务启动失败排查
- **WHEN** 新手执行启动命令后服务异常
- **THEN** 文档 SHALL 提供排查步骤：
  1. 检查容器日志：`docker compose logs python-ai-talk`
  2. 检查容器状态：`docker compose ps`
  3. 检查网络连通性：`docker network inspect`
  4. 检查环境变量：`docker compose config`

#### Scenario: 镜像拉取失败排查
- **WHEN** 新手执行镜像拉取失败
- **THEN** 文档 SHALL 提供排查步骤：
  1. 检查 ACR 登录状态
  2. 检查网络连通性
  3. 检查镜像版本是否存在

#### Scenario: 服务健康检查失败排查
- **WHEN** 健康检查持续失败
- **THEN** 文档 SHALL 提供排查步骤：
  1. 检查端口监听状态
  2. 检查向量库是否已构建
  3. 检查依赖服务是否可用

### Requirement: 提供环境准备说明

文档 SHALL 包含部署前的环境准备步骤，确保基础设施就绪。

#### Scenario: Docker 安装验证
- **WHEN** 新手需要验证 Docker 是否正确安装
- **THEN** 文档 SHALL 提供验证命令：
  ```bash
  docker --version
  docker compose version
  ```

#### Scenario: Docker 网络创建
- **WHEN** 新手需要创建 Docker 网络
- **THEN** 文档 SHALL 提供创建命令：
  ```bash
  docker network create python-ai-talk-net
  ```

#### Scenario: ACR 登录
- **WHEN** 运维人员需要登录阿里云容器镜像服务
- **THEN** 文档 SHALL 提供登录命令：
  ```bash
  docker login --username=<ACR_USERNAME> \
    crpi-lff3xynwzvqxxxjk-vpc.cn-hangzhou.personal.cr.aliyuncs.com
  ```

### Requirement: 文档结构清晰

文档 SHALL 采用清晰的章节结构，便于新手按步骤操作。

#### Scenario: 文档章节结构
- **WHEN** 新手打开部署指南文档
- **THEN** 文档 SHALL 包含以下章节：
  1. 概述（项目简介、部署架构）
  2. 目录结构说明
  3. 环境准备（Docker 安装、网络创建、ACR 登录）
  4. 本地开发环境部署
  5. 测试环境部署
  6. 生产环境部署
  7. 环境变量配置说明
  8. 常见问题解答
  9. 附录（参考链接）