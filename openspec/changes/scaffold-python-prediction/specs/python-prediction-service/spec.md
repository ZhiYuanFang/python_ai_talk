## ADDED Requirements

### Requirement: python-prediction 独立服务进程
本仓 SHALL 提供独立微服务 `python-prediction`，其应用代码位于仓库根下 `prediction/` 包，入口可由 `uvicorn prediction.main:app` 启动。该服务 MUST NOT 与 `app/`（python-ai-talk）共享同一进程。

#### Scenario: 独立入口存在
- **WHEN** 运维或开发者检查仓库
- **THEN** 存在 `prediction/main.py`（或等价）可启动的 FastAPI 应用
- **AND** 现有 `app/main.py` 仍作为 python-ai-talk 入口保留

### Requirement: 健康检查标识服务名
`python-prediction` SHALL 提供 HTTP 健康检查接口，成功时返回 HTTP 200，且响应体中 MUST 包含标识本服务的字段（如 `"service": "python-prediction"`）。健康检查路径 MUST 与 Docker healthcheck 使用的路径一致（默认 `GET /v1/health`）。

#### Scenario: 健康检查成功
- **WHEN** 客户端请求 `GET /v1/health`（或 compose healthcheck 等价探测）
- **THEN** 响应 HTTP 200
- **AND** 响应表明服务为 `python-prediction` 且状态为健康

### Requirement: 监听端口 8001
`python-prediction` 容器内进程 SHALL 默认监听 `0.0.0.0:8001`。

#### Scenario: 容器内端口
- **WHEN** 服务以 Docker 默认命令启动
- **THEN** 健康检查可在容器内 `http://127.0.0.1:8001/v1/health` 探测成功

### Requirement: 骨架期不含预测模型业务 API
本变更范围内，`python-prediction` MUST NOT 实现预测机器学习模型的训练或推理业务接口；模型能力留待后续变更。允许仅有健康检查与空壳路由结构。

#### Scenario: 无模型推理契约
- **WHEN** 本变更合并后检查对外 API
- **THEN** 不存在已承诺的预测推理业务路径作为本变更交付物
- **AND** 健康检查仍可用
