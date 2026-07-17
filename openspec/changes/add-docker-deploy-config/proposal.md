# Proposal: 添加 Docker 多环境部署配置

## Why

当前项目仅有单一 `docker-compose.yml` 用于本地开发，缺乏测试和生产环境的部署配置。同时缺少面向新手的部署指南文档，导致团队成员在 Linux 服务器部署时需要反复查询命令和配置，效率较低。

需要建立与兄弟仓 go_ai_talk 一致的多环境部署体系，实现本地、测试、生产三套环境的标准化配置分离。

## What Changes

- 新增 `docker-compose.test.yml` 测试环境 overlay（端口 18000、项目名 `python-ai-talk-test`）
- 新增 `docker-compose.prod.yml` 生产环境 overlay（端口 8000、项目名 `python-ai-talk-prod`）
- 新增 `docker-compose.local.yml` 本地环境 overlay（从现有 docker-compose.yml 抽离）
- 填充 `env/.env.local` 本地开发环境变量
- 填充 `env/.env.test` 测试环境变量（ACR 测试仓库、Redis 单节点、服务发现地址）
- 填充 `env/.env.prod` 生产环境变量（ACR 生产仓库、Redis Cluster、服务发现地址）
- 新增 `docs/deploy-guide.md` 部署指南文档（面向新手，包含环境准备、启动命令、常见问题）

## Capabilities

### New Capabilities

- `deploy-guide`: 部署指南文档，涵盖本地开发、测试、生产三套环境的完整部署流程，包含环境变量配置、Docker 命令、常见问题解答

### Modified Capabilities

（无现有能力修改）

## Impact

**新增文件：**
- `docker-compose.local.yml`
- `docker-compose.test.yml`
- `docker-compose.prod.yml`
- `env/.env.local`
- `env/.env.test`
- `env/.env.prod`
- `docs/deploy-guide.md`

**修改文件：**
- `docker-compose.yml` 改为基线配置（仅定义服务骨架和环境变量引用）

**依赖变更：**
- 测试环境镜像推送到 `pangbao-test` ACR 仓库
- 生产环境镜像推送到 `pangbao-release` ACR 仓库
- 与 go_ai_talk 共享 DeepSeek/GLM API Key
- 服务发现依赖 go_ai_talk 的 history-service、device-service、voice-service