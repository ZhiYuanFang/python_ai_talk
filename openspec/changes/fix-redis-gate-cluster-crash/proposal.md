## Why

生产环境 Redis 集群模式下，`redis_gate.py` 在模块导入阶段就会崩溃（`ValueError: Port could not be cast to integer value`），导致 uvicorn worker 进程反复重启，CPU 被重启风暴占满，服务完全不可用。同时存在同步/异步 Redis 客户端混用、模块级单例初始化过早等多个叠加问题，需要系统性修复。

## What Changes

- 修复 `RedisCluster.from_url()` 不支持逗号分隔多节点 URL 的 bug，改用 `startup_nodes` 方式创建集群客户端
- 修复 Redis 客户端同步/异步混用问题，统一使用异步客户端（`redis.asyncio`）
- 将模块级单例（`llm_client`、`vector_store`、`http_client` 等）改为延迟初始化（lazy init），避免 import 阶段连接外部依赖导致服务启动失败
- 修复 Docker healthcheck 路径错误（`/health` → `/v1/health`），避免容器被误判为 unhealthy
- 调整 Dockerfile 中 uvicorn `--workers` 参数从 2 改为 1，降低基线 CPU/内存占用（AI 模型服务单 worker 已足够）

## Capabilities

### New Capabilities

- `redis-gate-cluster-fix`: 修复 Redis 闸门集群模式连接 bug，确保生产集群环境下服务正常启动
- `lazy-singleton-init`: 模块级单例延迟初始化机制，import 阶段不连接外部依赖，提升服务启动健壮性
- `healthcheck-path-fix`: 修复 Docker 健康检查路径，确保容器健康状态正确上报

### Modified Capabilities

（无现有规格需要修改，本次变更为 bug 修复和健壮性增强，不改变 API 行为）

## Impact

- **代码文件**：
  - `app/shared/redis_gate.py`：修复集群连接逻辑、统一异步客户端、清理 import
  - `app/shared/llm_client.py`：改为延迟初始化 `RedisGate`
  - `app/shared/vector_store.py`：改为延迟初始化
  - `app/shared/http_client.py`：改为延迟初始化
  - `app/feeding/services/event_cache.py`：改为延迟初始化
  - `app/feeding/services/event_vector_store.py`：改为延迟初始化
  - `Dockerfile`：修复 healthcheck 路径、调整 workers 数量
- **API**：无接口变更，纯内部修复
- **依赖**：无新增依赖
- **部署**：Docker 镜像需要重新构建
