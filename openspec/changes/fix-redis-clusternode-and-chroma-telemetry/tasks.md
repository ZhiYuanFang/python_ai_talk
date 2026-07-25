## 1. Redis 集群 ClusterNode 与 URL 解析

- [x] 1.1 在 `app/shared/redis_gate.py` 从 `redis.asyncio.cluster` 导入 `ClusterNode`，将 `startup_nodes` 改为 `ClusterNode(host, port)` 列表
- [x] 1.2 修正逗号分隔 URL 解析：无 `://` 的 `host:port`（可带 `/db`）段也写入 `startup_nodes`，满足三节点全部解析
- [x] 1.3 保留从首节点 URL 解析 password（及既有超时/`decode_responses` 行为），加中文注释说明集群解析规则

## 2. Chroma telemetry 静音与环境变量

- [x] 2.1 在 `app/main.py` 尽早将 `chromadb.telemetry.product.posthog` logger 设为 `CRITICAL`，并设置 `ANONYMIZED_TELEMETRY=False`（替换或不再依赖 `CHROMA_TELEMETRY`）
- [x] 2.2 更新 `docker-compose.yml`：增加 `ANONYMIZED_TELEMETRY=False`；停止把 `CHROMA_TELEMETRY` 当作有效开关
- [x] 2.3 在 `pyproject.toml` 增加 `posthog = ">=2.4.0,<6.0.0"`；若 Dockerfile 单独 pip 安装 chromadb，同步钉住 posthog

## 3. 验证

- [x] 3.1 用模拟集群 URL（三节点格式）实例化 `RedisGate`，确认无 `AttributeError` 且解析出三个节点
- [x] 3.2 确认单机 `redis_url` 路径仍可创建客户端（不要求真连成功也可做构造级检查）
- [x] 3.3 触发向量查询路径后，日志中不再出现 `chromadb.telemetry.product.posthog` 的 ERROR
