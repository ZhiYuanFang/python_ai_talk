## ADDED Requirements

### Requirement: Docker healthcheck 路径正确
Dockerfile 中的 HEALTHCHECK 命令 SHALL 使用正确的健康检查路径 `/v1/health`，与 FastAPI 路由定义保持一致。

#### Scenario: 容器健康检查成功
- **WHEN** 容器正常运行且服务已启动
- **THEN** Docker healthcheck SHALL 返回 0（成功）
- **AND** 容器状态 SHALL 显示为 healthy

#### Scenario: 服务未启动时健康检查失败
- **WHEN** 服务未启动或已崩溃
- **THEN** Docker healthcheck SHALL 返回非 0（失败）
- **AND** 达到重试次数后容器状态 SHALL 变为 unhealthy

### Requirement: uvicorn worker 数量配置合理
Docker 部署的 uvicorn worker 数量 SHALL 配置为 1，避免多 worker 导致的内存和 CPU 浪费。

#### Scenario: 单 worker 模式启动
- **WHEN** 容器启动
- **THEN** uvicorn SHALL 以 1 个 worker 进程运行
- **AND** 内存占用 SHALL 低于多 worker 模式
