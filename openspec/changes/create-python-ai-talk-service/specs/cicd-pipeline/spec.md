## ADDED Requirements

### Requirement: GitHub Actions 工作流
系统 SHALL 提供 `.github/workflows/docker-acr.yml`，支持 tag 触发自动构建推送阿里云 ACR。

#### Scenario: tag 触发构建
- **WHEN** 推送 git tag `v1.0.0-rc.1`
- **THEN** GitHub Actions 自动触发构建工作流

#### Scenario: 环境判断
- **WHEN** tag 为 `v1.0.0-rc.1` 或 `v1.0.0-beta.1`
- **THEN** 工作流判断为测试环境，使用 test 环境的 REGISTRY

#### Scenario: 生产环境判断
- **WHEN** tag 为纯数字版本（如 `v1.0.0`）
- **THEN** 工作流判断为生产环境，使用 prod 环境的 REGISTRY

### Requirement: ACR 登录
系统 SHALL 使用 GitHub Secrets 中的 ACR_USERNAME 和 ACR_PASSWORD 登录阿里云 ACR。

#### Scenario: 登录成功
- **WHEN** 工作流执行登录步骤
- **THEN** 使用 Secrets 中的凭证成功登录 ACR

#### Scenario: 登录失败
- **WHEN** Secrets 凭证错误
- **THEN** 工作流失败并输出错误信息

### Requirement: 镜像构建与推送
系统 SHALL 构建 Docker 镜像并推送到阿里云 ACR。

#### Scenario: 构建生产镜像
- **WHEN** 工作流执行构建步骤
- **THEN** 使用 Dockerfile 构建生产镜像

#### Scenario: 推送镜像
- **WHEN** 工作流执行推送步骤
- **THEN** 镜像被推送到 `${REGISTRY}/python-ai-talk:${tag}`

#### Scenario: 多标签推送
- **WHEN** 工作流执行推送步骤
- **THEN** 镜像同时推送到 `${REGISTRY}/python-ai-talk:${tag}` 和 `${REGISTRY}/python-ai-talk:${tag}-<sha>`

### Requirement: 手动触发
系统 SHALL 支持通过 workflow_dispatch 手动触发构建。

#### Scenario: 手动触发构建
- **WHEN** 在 GitHub Actions 页面手动触发工作流
- **THEN** 工作流执行构建推送流程

### Requirement: 构建取消
系统 SHALL 在新的推送触发时自动取消之前正在运行的工作流。

#### Scenario: 自动取消旧工作流
- **WHEN** 新的 tag 推送触发工作流，而之前的工作流正在运行
- **THEN** 之前的工作流被自动取消

### Requirement: 构建范围
系统 SHALL 支持单服务构建（类似 go_ai_talk 的 `v1.0.0-rc.2+ucg` 格式）。

#### Scenario: 单服务构建
- **WHEN** tag 为 `v1.0.0-rc.1+python`
- **THEN** 工作流仅构建 python-ai-talk 服务

#### Scenario: 全量构建
- **WHEN** tag 不包含 `+python`
- **THEN** 工作流跳过构建（仅 Python 仓库触发）