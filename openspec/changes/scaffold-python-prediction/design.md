## Context

本仓已是被 go_ai_talk 调用的智能内核微服务 `python-ai-talk`：Compose 采用基线 + local/test/prod overlay，CI 将镜像推到 ACR 仓库 `python-ai-talk`。仓库内仍只有一个可构建服务；现有预测播报走 `app/feeding` 本地算法，与即将独立的 ML 预测服务解耦。

Go 侧参考（`go_ai_talk`）：
- 多 `Dockerfile.<service>` + `docker-compose.microservices*.yml` overlay
- `.github/workflows/docker-acr.yml` 用 `vX.Y.Z[+别名]` / `workflow_dispatch.services` 生成动态 matrix 推 ACR

本变更按探索结论采用 **A1 最小扰动 monorepo**：不搬迁 `app/`。

## Goals / Non-Goals

**Goals:**
- 本仓同时承载两个可独立构建、独立推送、独立部署的服务：`python-ai-talk`、`python-prediction`
- prediction 提供可健康检查的 FastAPI 骨架（端口 8001）
- CI 对齐 Go：按服务别名选择性 build/push
- Compose 三环境均能拉起双服务并加入既有外部网络

**Non-Goals:**
- 不实现预测模型训练/推理业务 API
- 不改写 `predict_algo` / `speak_predict` 等现有意图预测路径
- 不要求本轮修改 go_ai_talk 仓库
- 不做 `app/` → `services/` 大目录搬迁
- 不为 prediction stub 引入 torch / sklearn 等 ML 重依赖

## Decisions

### 1. 目录：`app/` 保留 + 新建 `prediction/`
- **选择**：`prediction/main.py` 作为 `uvicorn prediction.main:app` 入口；健康检查返回 `service: python-prediction`
- **替代**：`services/python-prediction/`（更像 Go，但骨架期多一层无必要路径）
- **理由**：零搬迁 talk；包名短、与 ACR 仓库名语义对应

### 2. Dockerfile 拆分
- **选择**：
  - `Dockerfile.python-ai-talk` ← 现有 `Dockerfile` 迁入（内容不变）
  - `Dockerfile.python-prediction` ← 轻量：`python:3.12-slim` + fastapi/uvicorn/wget，`CMD` 起 prediction
  - 删除或保留薄包装：实现时以 compose/CI 指向新文件名为准；根目录旧 `Dockerfile` 可改为指向说明或删除（tasks 中明确）
- **理由**：镜像依赖隔离；避免 stub 继承 talk 的 torch/chroma 体积

### 3. Compose 双服务 + 端口
| 服务 | 容器端口 | local/prod 宿主机 | test 宿主机 | 本地 image |
|------|----------|-------------------|-------------|------------|
| python-ai-talk | 8000 | 8000 | 18000 | `go-ai-talk/python-ai-talk:local` |
| python-prediction | 8001 | 8001 | 18001 | `go-ai-talk/python-prediction:local` |

- project 名保持 `python-ai-talk-{local,test,prod}`
- 网络：prod → `go-ai-talk-net`；test → `go-ai-talk-test-net`；local 与 talk 一致加入 `go-ai-talk-net`
- 实现时顺带把 local overlay 的 networks 写法对齐 prod/test（具名 external network），避免仅嵌在 service 下的残缺结构

### 4. CI：Go 同款构建范围
- 别名映射：
  - `talk` / `ai-talk` / `python-ai-talk` → id `python-ai-talk` → `Dockerfile.python-ai-talk`
  - `prediction` / `python-prediction` → id `python-prediction` → `Dockerfile.python-prediction`
  - `all` 或空 scope → 两者
- tag：`primary_tag` 为 `+` 前 base；ACR 推送 `${REGISTRY}/<id>:${primary_tag}` 与 `${REGISTRY}/<id>:${GITHUB_SHA}`
- `workflow_dispatch` 增加可选 `services` 输入（与 Go 一致）
- 修正基线中过时的「无 `+python` 则跳过构建」语义

### 5. 跨服务调用预留（可选、弱绑定）
- 在基线 compose / `.env.example` 为 talk 预留 `PYTHON_PREDICTION_URL=http://python-prediction:8001`
- 本轮 talk 代码 **不** 强制读取或调用；下一轮模型提案再接线
- prediction 暂不依赖 history/device 等兄弟服务 URL

### 6. 依赖管理
- 保持根 `pyproject.toml` 服务 talk；prediction Dockerfile 用 pip 钉最小依赖，避免污染 talk 依赖树
- 后续若共享代码，再抽 `shared` 或 poetry packages——不在本轮

## Risks / Trade-offs

- **[Risk] ACR 尚未创建 `python-prediction` 仓库 → push 失败**  
  → Mitigation：部署文档注明需在 test/prod 命名空间预建仓库；CI 失败信息指向 runbook
- **[Risk] 旧脚本仍 `docker build -f Dockerfile`**  
  → Mitigation：deploy-guide / README 更新；可选保留根 `Dockerfile` 为 talk 的副本或 symlink 式说明（Windows 上优先「同内容文件 + 文档」，避免 symlink 坑）
- **[Risk] 同 compose 一键 up 会同时起两个服务，本地资源变重**  
  → Mitigation：可用 `docker compose up python-ai-talk` 单起；CI 可用 `+talk` / `+prediction` 分推
- **[Trade-off] project 名仍叫 `python-ai-talk-*`**  
  → 少改运维习惯；语义上略偏单服务，可在文档标明「含多 Python 微服务」
- **[Trade-off] prediction 与 talk 同仓发布节奏绑定**  
  → 用 `+prediction` 缓解；真要完全独立生命周期再评估拆仓

## Migration Plan

1. 合并代码：双 Dockerfile、双服务 compose、workflow、prediction stub
2. ACR：在 test/prod 命名空间创建 `python-prediction` 仓库
3. 服务器：更新 `env/.env.*`（如需），`pull && up -d --no-build`（两服务）
4. 验证：`/v1/health` 在 8000 与 8001（测试 18000/18001）均 healthy
5. 回滚：overlay 可暂时 scale prediction 为 0 或不 pull prediction；talk 镜像路径变更后需确保仍指向 `Dockerfile.python-ai-talk` 产物

## Open Questions

- 根目录是否保留名为 `Dockerfile` 的 talk 副本以兼容旧命令？（默认：**不保留**，文档改指向 `Dockerfile.python-ai-talk`）
- talk 是否本轮写入读取 `PYTHON_PREDICTION_URL` 的 settings 字段？（默认：**仅 env/compose 预留，应用代码不读**）
