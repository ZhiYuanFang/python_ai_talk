## Context

`fix-redis-gate-cluster-crash` 已将集群连接从 `RedisCluster.from_url()` 改为手动 `startup_nodes`，并完成 lazy init。生产新错误表明：`redis-py` 5.x 的 `RedisCluster.__init__` 对 `startup_nodes` 期望 `ClusterNode` 实例，当前传入的 `{"host","port"}` dict 会在访问 `node.host` 时崩溃。Clinic `/v1/clinic/stream` 在图执行完成后首次创建 `RedisGate` 时暴露该问题。

同时日志中 `chromadb.telemetry.product.posthog` 持续 ERROR：chromadb 0.4.x 调用旧版 `posthog.capture` 签名，与 posthog≥6 不兼容。代码已设 `Settings(anonymized_telemetry=False)`，且使用了无效环境变量名 `CHROMA_TELEMETRY`。

约束：不改对外 HTTP API；不引入与 Intent 确认流相关的改动；保持中文业务注释风格。

## Goals / Non-Goals

**Goals:**
- 集群 URL 下 `RedisGate()` 可成功创建异步 `RedisCluster`，Clinic/LLM 闸门可用
- 逗号分隔 URL（含无 scheme 的后续节点）解析出全部 startup 节点
- 消除 chromadb posthog telemetry ERROR 刷屏；环境变量名与 chromadb 对齐

**Non-Goals:**
- Intent `thread_id` / MemorySaver / confirm 接线（后续 change）
- 升级 chromadb 主版本
- 改造闸门业务语义或 Key 格式
- 多实例 Redis checkpointer

## Decisions

### 决策 1：`startup_nodes` 使用 `ClusterNode`

**选择**：`from redis.asyncio.cluster import RedisCluster, ClusterNode`，解析后 `ClusterNode(host=..., port=...)`。

**替代**：继续传 dict —— 在 redis-py 5.x 下必崩，排除。

**理由**：与当前依赖 `redis = "^5.2.0"` 的公开 API 一致；修正此前 design「dict 即可」的错误假设。

### 决策 2：无 scheme 节点的 URL 解析

**选择**：逗号拆分后，对缺少 `://` 的段按 `host:port`（可带 `/db`）解析；首段仍用 `urlparse` 取 password 等公共参数。

**替代**：要求运维改成每个节点都带 `redis://` —— 与现网/既有文档格式冲突，排除。

**理由**：规格与现网格式为 `redis://h1:7001,h2:7002,h3:7003`；只解析首节点会削弱 startup 冗余。

### 决策 3：Telemetry 双保险（logger + 可选 pin）

**选择**：
1. 启动早期将 `chromadb.telemetry.product.posthog` logger 设为 `CRITICAL`（对齐 `silence-health-access-log`）
2. `os.environ["ANONYMIZED_TELEMETRY"]="False"`，compose 同步；移除或停止依赖假名 `CHROMA_TELEMETRY`
3. 在 `pyproject.toml` / Dockerfile 增加 `posthog>=2.4,<6`，避免错误调用路径

**替代**：仅改 Settings —— 已证明不够；仅升 chromadb —— 与钉 0.4.* 策略冲突。

**理由**：logger 立刻消噪音；pin 治本且风险低。

## Risks / Trade-offs

| 风险 | 缓解 |
|---|---|
| 集群 Lua `eval` 在部分 redis-py/集群配置下行为异常 | 冒烟验证 acquire/release；若失败再单独 change |
| 钉 posthog 与其他传递依赖冲突 | 构建时确认；失败则仅保留 logger 方案 |
| 仅 CRITICAL 静音会掩盖真故障 | 仅针对该 logger 名；不影响其他 chromadb 日志 |

## Migration Plan

1. 改 `redis_gate.py` 与 telemetry 启动/compose/依赖
2. 重建镜像或重启服务
3. 用集群 `REDIS_URL` 打 `/v1/clinic/stream`，确认无 `AttributeError`、无 posthog ERROR 刷屏
4. 回滚：回退镜像；配置侧无破坏性迁移

## Open Questions

1. 生产 Redis 是否带密码？当前从首节点 URL 解析 password，需在冒烟时确认 AUTH 成功。
2. `fix-redis-gate-cluster-crash` 未勾验证任务是否在本次一并勾完后归档，还是本 change 独立验证后留下旧 change 另行归档？
