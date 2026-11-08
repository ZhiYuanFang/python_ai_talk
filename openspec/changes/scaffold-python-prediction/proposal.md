## Why

本仓已作为微服务 `python-ai-talk` 部署，但仓库仍是单服务形态：Compose 只有一个 service，ACR 工作流写死推送一个镜像，无法按 Go 侧同款 `v*+服务别名` 选择性构建。需要先在本仓搭好多服务骨架，并新增独立服务 `python-prediction`（预测机器学习模型，业务细节下一轮再补），以便后续独立发版、独立镜像体积与独立依赖，而不把 ML 运行时绑进现有 LLM/LangGraph 镜像。

## What Changes

- 本仓升级为 **最小扰动 monorepo**：保留现有 `app/` 作为 `python-ai-talk`；新增 `prediction/` 包作为 `python-prediction` 服务入口（健康检查骨架，不含模型实现）。
- Compose 基线与 local/test/prod overlay 同时定义两个服务：`python-ai-talk`（8000 / 测试 18000）与 `python-prediction`（8001 / 测试 18001），共用既有外部网络约定。
- Dockerfile 拆分为 `Dockerfile.python-ai-talk`（由现有 Dockerfile 迁出）与轻量 `Dockerfile.python-prediction`（stub，不引入 ML 重依赖）。
- `.github/workflows/docker-acr.yml` 对齐 go_ai_talk：按 tag 后缀 / workflow_dispatch 解析构建范围，matrix 推送 `${REGISTRY}/python-ai-talk` 与/或 `${REGISTRY}/python-prediction`。
- **部署分版本（路径 1）**：test/prod overlay 不再共用单一 `IMAGE_TAG`；改为 `PYTHON_AI_TALK_IMAGE_TAG` 与 `PYTHON_PREDICTION_IMAGE_TAG`，两服务可钉不同 ACR tag。过渡期 talk 可用 `${PYTHON_AI_TALK_IMAGE_TAG:-${IMAGE_TAG}}` 回退旧变量；prediction MUST 使用显式 `PYTHON_PREDICTION_IMAGE_TAG`。
- 更新部署文档与 `.env.example` 中与双服务、端口、双 tag、可选 `PYTHON_PREDICTION_URL` 相关的说明。
- **不**迁移或改写现有 `predict_*` / `speak_predict` 行为；**不**实现预测模型推理 API；**不**改为独立 git tag 发布线（路径 2）。

## Capabilities

### New Capabilities
- `python-prediction-service`: 新微服务骨架（进程入口、健康检查、服务标识、独立镜像与端口约定）

### Modified Capabilities
- `docker-deployment`: Compose 从单服务扩展为双服务；新增 prediction 的 image / ports / networks / healthcheck 约定；talk Dockerfile 路径调整；test/prod 按服务独立镜像 tag 变量
- `cicd-pipeline`: 构建范围从旧 `+python` 语义改为 Go 同款多服务别名（`talk` / `prediction` / `all`），支持按服务推送 ACR；文档/注释对齐「CI primary_tag ↔ 对应服务的 `*_IMAGE_TAG`」而非单一 `IMAGE_TAG`

## Impact

- **代码**：新增 `prediction/` 轻量 FastAPI 应用；现有 `app/` 逻辑不变（可选仅 env 预留 `PYTHON_PREDICTION_URL`，本轮不发起调用）
- **部署**：`docker-compose*.yml`、Dockerfile 文件名、`docs/deploy-guide.md`、`.env.example`；`env/.env.*` 需补两服务 tag（运维）
- **CI**：`.github/workflows/docker-acr.yml`；GitHub Environments 的 `REGISTRY` 命名空间下需具备 `python-prediction` 仓库（运维侧）
- **兄弟仓**：本轮不要求改 go_ai_talk；prediction 与 talk 一样加入 `go-ai-talk-net` / `go-ai-talk-test-net` 即可同网可达
- **兼容性**：本地/测试/生产启动命令仍为基线 + overlay；project 名保持 `python-ai-talk-{local,test,prod}`；旧单服务 `Dockerfile` 路径变更对习惯 `docker build -f Dockerfile` 的脚本为 **BREAKING**（需改用 `Dockerfile.python-ai-talk`）；共用 `IMAGE_TAG` 拉两服务为 **BREAKING**（改为分服务 tag，talk 过渡期可回退）
