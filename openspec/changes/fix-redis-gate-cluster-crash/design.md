## Context

### 当前问题

生产环境 Redis 使用三节点集群模式（`redis://redis-node-1:7001,redis-node-2:7002,redis-node-3:7003`），Python AI 服务在启动时崩溃：

```
ValueError: Port could not be cast to integer value as '7001,redis-node-2:7002,redis-node-3:7003'
```

崩溃发生在模块导入阶段（`llm_client = LLMClient()` → `RedisGate()` → `RedisCluster.from_url()`），导致 uvicorn worker 进程反复崩溃重启，形成 CPU 重启风暴。

### 现有代码问题

1. **redis_gate.py 集群连接 bug**：`RedisCluster.from_url()` 只能解析单个 URL，不能处理逗号分隔的多节点地址。代码中先调用 `from_url()` 失败后才手动解析 `startup_nodes`，但第一次调用已经抛异常了。

2. **同步/异步客户端混用**：第 18 行 `import redis`（同步），第 20 行 `import redis.asyncio as redis` 覆盖了前面的 import。集群分支用的是同步 `RedisCluster`，非集群分支用的是异步 `redis.Redis`，但所有方法都用 `await` 调用。

3. **模块级单例过早初始化**：`llm_client`、`vector_store`、`http_client`、`event_cache` 等单例在 import 时就实例化并连接外部依赖（Redis、ChromaDB 等），任何外部依赖不可用都会导致服务完全无法启动。

4. **healthcheck 路径错误**：Dockerfile 中健康检查路径是 `/health`，但实际路由是 `/v1/health`，导致容器永远显示 unhealthy。

5. **uvicorn workers=2**：Dockerfile 配置 2 个 worker，每个 worker 独立加载 BGE 模型和 ChromaDB，内存和 CPU 占用翻倍。对于 AI 推理型服务，单 worker 已足够（推理主要受 LLM API 延迟限制，而非 CPU 瓶颈）。

### 约束

- 不能改变对外 API 接口行为
- 不能新增第三方依赖
- 保持代码的中文业务逻辑注释风格
- 兼容单机 Redis 和集群 Redis 两种部署模式

## Goals / Non-Goals

**Goals:**
- 修复 Redis 集群模式下服务启动崩溃的问题
- 统一使用异步 Redis 客户端，消除同步/异步混用
- 实现模块级单例延迟初始化，提升服务启动健壮性
- 修复 Docker healthcheck 路径
- 降低基线 CPU/内存占用（调整 workers 数量）

**Non-Goals:**
- 不重构业务逻辑
- 不修改 API 接口定义
- 不新增缓存层或消息队列
- 不引入新的依赖库

## Decisions

### 决策 1：Redis 集群连接方式 — 手动解析 startup_nodes

**选择**：手动解析逗号分隔的 URL 列表，构建 `startup_nodes`，使用 `redis.asyncio.cluster.RedisCluster` 创建集群客户端。

**替代方案**：
- `RedisCluster.from_url()` — 不支持多节点 URL，排除
- 只连一个节点自动发现集群 — 存在单点风险，排除

**理由**：
- `redis-py` 的集群客户端需要 `startup_nodes` 列表格式，每个节点是 `{"host": ..., "port": ...}` 的字典
- 手动解析可控性强，能处理各种格式的输入
- 与现有代码中已有的解析逻辑一致（只是之前被 `from_url()` 挡住了没执行到）

### 决策 2：统一使用异步 Redis 客户端

**选择**：全部使用 `redis.asyncio` 包，移除同步 `redis` import。集群客户端使用 `redis.asyncio.cluster.RedisCluster`。

**替代方案**：
- 全部用同步客户端 + run_in_executor — 增加复杂度，排除
- 保留混用 — 运行时会出错，排除

**理由**：
- FastAPI 是异步框架，所有路由都是 async 函数
- Redis 调用应该是非阻塞的，避免阻塞事件循环
- 代码中已经在用 `await self._redis.eval(...)`，说明设计上就是异步的

### 决策 3：单例延迟初始化策略 — 属性访问时初始化

**选择**：使用 `__getattr__` 或 lazy property 模式，在第一次访问单例实例的方法/属性时才执行初始化。对于 `llm_client`，在第一次调用 `invoke()` 或 `stream()` 时才创建 `RedisGate`。

**替代方案**：
- 显式 `init()` 方法 — 需要调用方手动调用，容易遗漏，排除
- 启动时 try/except 忽略错误 — 隐藏问题，排查困难，排除

**理由**：
- 透明性：调用方不需要知道初始化时机
- 健壮性：import 阶段不连接外部依赖，服务至少能启动、响应健康检查
- 失败时请求会返回错误，而不是服务直接起不来

### 决策 4：uvicorn workers 调整为 1

**选择**：Dockerfile 中 `--workers 2` 改为 `--workers 1`。

**替代方案**：
- 保持 2 — CPU/内存占用高，没有必要，排除
- 动态调整 — 增加复杂度，排除

**理由**：
- 本服务是 IO 密集型（调用 LLM API、HTTP 调用兄弟仓），而非 CPU 密集型
- 真正的 CPU 消耗（Embedding 推理）量不大，单 worker 足够
- 每个 worker 独立加载 BGE 模型（~100MB）和 ChromaDB，2 个 worker 内存多占 ~200MB+
- 单 worker 下 ChromaDB 不会有并发写入问题

## Risks / Trade-offs

| 风险 | 影响 | 缓解措施 |
|---|---|---|
| 延迟初始化后，第一次请求会更慢 | 用户体验 | 在启动钩子中预热关键单例（vector_store），不阻塞启动但后台初始化 |
| 单 worker 下高并发请求排队 | 性能 | 当前流量不大，单 worker 足够；未来可根据压力测试结果调整 |
| Redis 集群客户端 API 差异 | 功能异常 | 验证 `eval` 方法在集群模式下是否可用，必要时调整 Lua 脚本执行方式 |
| 修改 import 顺序可能引入循环依赖 | 启动失败 | 修改后完整测试 import 链路，确保无循环依赖 |

## Migration Plan

1. 修改 `redis_gate.py`，修复集群连接逻辑和异步客户端统一
2. 修改各单例模块，实现延迟初始化
3. 修改 `Dockerfile`，修复 healthcheck 路径和 workers 数量
4. 本地验证：单机 Redis 模式 + 模拟集群 URL 模式
5. 构建 Docker 镜像，测试容器启动和健康检查
6. 灰度部署到测试环境验证
7. 回滚方案：保留旧版本镜像，发现问题可快速回滚

## Open Questions

1. 生产环境 Redis 集群是否启用了密码认证？当前代码未处理 AUTH 配置
2. 向量存储（vector_store 和 event_vector_store）是否需要也改为共享同一个 Embedding 模型实例？（当前是各自加载一次）
3. healthcheck 接口是否应该检查 Redis 和向量库的可用性？还是只检查进程存活即可？
