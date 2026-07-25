## Why

生产环境 Clinic 流式接口在首次调用 LLM 时创建 `RedisGate`，因 `startup_nodes` 传入 `dict` 而非 `ClusterNode`，触发 `AttributeError: 'dict' object has no attribute 'host'`，SSE 中途崩溃。同时 ChromaDB 0.4.x 与 posthog≥6 的 `capture()` 签名不兼容，每次向量查询都打印 ERROR 级 telemetry 噪音（`Settings(anonymized_telemetry=False)` 与错误的 `CHROMA_TELEMETRY` 环境变量均无法消除）。先修复这两项运维/可用性故障；Intent 确认流接线另开 change。

## What Changes

- 修正 Redis 集群闸门：`startup_nodes` 使用 `ClusterNode`；逗号分隔多节点 URL 中无 scheme 的 `host:port` 段也能正确解析出全部节点
- 静音 Chroma posthog telemetry ERROR：进程启动时提升该 logger 级别；纠正环境变量为 `ANONYMIZED_TELEMETRY`；可选钉住 `posthog<6` 从根上避免调用失败
- **不包含**：Intent `thread_id` / MemorySaver / confirm 接线（留给后续 change）

## Capabilities

### New Capabilities

- `redis-gate-clusternode`: Redis 集群闸门使用 `ClusterNode` 与完整多节点 URL 解析，确保 Clinic/LLM 并发闸门可创建
- `silence-chroma-telemetry`: 消除 chromadb posthog telemetry ERROR 日志噪音，并纠正遥测相关环境变量

### Modified Capabilities

（无：`openspec/specs/` 下无已归档的对应能力需改需求；此前 `fix-redis-gate-cluster-crash` 仍为未归档 change，本次为针对生产新症状的增量修复）

## Impact

- **代码**：`app/shared/redis_gate.py`；`app/main.py`；`docker-compose.yml`；可选 `pyproject.toml` / `Dockerfile`（`posthog` 约束）
- **API**：无对外接口变更
- **依赖**：可选增加 `posthog>=2.4,<6` 约束（chromadb 传递依赖）
- **部署**：需重建/重启容器后验证 Clinic stream 与日志
- **关联**：补强/延续 `fix-redis-gate-cluster-crash` 未验证完的集群路径；不替代 Intent 确认流修复
