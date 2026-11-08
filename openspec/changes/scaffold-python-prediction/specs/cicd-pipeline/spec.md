## MODIFIED Requirements

### Requirement: 镜像构建与推送
系统 SHALL 按构建 matrix 为每个待构建服务构建 Docker 镜像并推送到阿里云 ACR。每个服务 MUST 使用对应的 Dockerfile（`Dockerfile.python-ai-talk` 或 `Dockerfile.python-prediction`）。每个服务 MUST 推送两个标签：`${REGISTRY}/<service-id>:${primary_tag}` 与 `${REGISTRY}/<service-id>:${GITHUB_SHA}`，其中 `<service-id>` 为 `python-ai-talk` 或 `python-prediction`，`primary_tag` 为去掉 `+` 构建后缀后的 base tag。

#### Scenario: 构建 talk 镜像
- **WHEN** 构建范围包含 `python-ai-talk`
- **THEN** 工作流使用 `Dockerfile.python-ai-talk` 构建并推送 `${REGISTRY}/python-ai-talk:${primary_tag}` 与 `${REGISTRY}/python-ai-talk:${GITHUB_SHA}`

#### Scenario: 构建 prediction 镜像
- **WHEN** 构建范围包含 `python-prediction`
- **THEN** 工作流使用 `Dockerfile.python-prediction` 构建并推送 `${REGISTRY}/python-prediction:${primary_tag}` 与 `${REGISTRY}/python-prediction:${GITHUB_SHA}`

### Requirement: 手动触发
系统 SHALL 支持通过 `workflow_dispatch` 手动触发构建，并允许指定目标环境、base `image_tag`，以及可选的逗号分隔服务别名列表（留空表示全量）。

#### Scenario: 手动触发全量
- **WHEN** 在 GitHub Actions 页面手动触发且 services 留空
- **THEN** 工作流构建并推送 `python-ai-talk` 与 `python-prediction`

#### Scenario: 手动触发单服务
- **WHEN** 手动触发且 services 填入 `prediction`
- **THEN** 工作流仅构建并推送 `python-prediction`

### Requirement: 构建范围
系统 SHALL 支持与 go_ai_talk 同构的构建范围：git tag 形如 `vMAJOR.MINOR.PATCH[-预发布][+别名列表]`，或 `workflow_dispatch` 的 services 输入。`+` 后为逗号分隔别名；支持 `talk` / `ai-talk` / `python-ai-talk`、`prediction` / `python-prediction`、`all`。无 `+` 后缀且非手动指定 services 时 MUST 全量构建两服务。`primary_tag`（ACR 主 tag）MUST 为 `+` 之前的 base tag，且 MUST 与服务器 `.env` 中 `IMAGE_TAG` 对齐语义。

#### Scenario: 全量 tag 构建
- **WHEN** 推送 git tag `v1.0.0-rc.1`（无 `+` 后缀）
- **THEN** 工作流构建并推送 `python-ai-talk` 与 `python-prediction` 至 test 环境 REGISTRY
- **AND** 镜像主 tag 为 `v1.0.0-rc.1`

#### Scenario: 仅 talk
- **WHEN** 推送 git tag `v1.0.0-rc.1+talk`
- **THEN** 工作流仅构建并推送 `python-ai-talk`
- **AND** 镜像主 tag 为 `v1.0.0-rc.1`

#### Scenario: 仅 prediction
- **WHEN** 推送 git tag `v1.0.0-rc.1+prediction`
- **THEN** 工作流仅构建并推送 `python-prediction`
- **AND** 镜像主 tag 为 `v1.0.0-rc.1`

#### Scenario: 生产全量
- **WHEN** 推送 git tag `v1.0.0`
- **THEN** 工作流在 prod 环境全量构建并推送两服务
