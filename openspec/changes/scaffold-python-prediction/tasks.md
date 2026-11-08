## 1. python-prediction 服务骨架

- [x] 1.1 新建 `prediction/` 包：`main.py` FastAPI 入口、`api/routes/health.py`（或等价），`GET /v1/health` 返回 healthy 且 `service=python-prediction`；代码含中文业务注释
- [x] 1.2 确认默认监听端口为 8001（uvicorn host 0.0.0.0 port 8001）

## 2. Dockerfile 拆分

- [x] 2.1 将现有根目录 `Dockerfile` 迁为 `Dockerfile.python-ai-talk`（内容保持 talk 构建逻辑）
- [x] 2.2 新增轻量 `Dockerfile.python-prediction`（fastapi/uvicorn/wget，无 torch/chroma/sentence-transformers）；EXPOSE 8001 与 healthcheck 对齐
- [x] 2.3 删除权威用途的旧根 `Dockerfile`（不保留同名副本；文档改指向新文件名）

## 3. Compose 双服务

- [x] 3.1 更新 `docker-compose.yml`：增加 `python-prediction` 服务骨架（build → `Dockerfile.python-prediction`、healthcheck、必要 env 占位）；`python-ai-talk` build 改为 `Dockerfile.python-ai-talk`；基线不写 ports；可选预留 `PYTHON_PREDICTION_URL`
- [x] 3.2 更新 `docker-compose.local.yml`：prediction 的 image/ports(8001)/extra_hosts；两服务 networks 写法对齐 prod（external `go-ai-talk-net`）
- [x] 3.3 更新 `docker-compose.test.yml`：prediction image `${REGISTRY}/python-prediction:${IMAGE_TAG}`、ports `18001:8001`、网络 `go-ai-talk-test-net`
- [x] 3.4 更新 `docker-compose.prod.yml`：prediction image `${REGISTRY}/python-prediction:${IMAGE_TAG}`、ports `8001:8001`、网络 `go-ai-talk-net`

## 4. CI（对齐 Go 构建范围）

- [x] 4.1 改造 `.github/workflows/docker-acr.yml`：解析 `+` 后缀与 `workflow_dispatch.services`；别名 `talk`/`prediction`/`all`（及全名兼容）；动态 matrix
- [x] 4.2 matrix 项分别使用对应 Dockerfile，推送 `${REGISTRY}/<id>:${primary_tag}` 与 `:${GITHUB_SHA}`；无后缀 = 全量两服务

## 5. 文档与 env 模板

- [x] 5.1 更新 `.env.example`：说明双服务、`IMAGE_TAG` 与可选 `PYTHON_PREDICTION_URL`
- [x] 5.2 更新 `docs/deploy-guide.md`（及必要时 README）：双服务启动、端口、按 `+talk`/`+prediction` 发版、ACR 需预建 `python-prediction` 仓库

## 6. 手工验收

- [x] 6.1 本地确认 talk 与 prediction 均可 build，且各自 `/v1/health` 可用（不编写自动化测试文件）
- [x] 6.2 确认未改动现有 `predict_*` / `speak_predict` 行为路径
