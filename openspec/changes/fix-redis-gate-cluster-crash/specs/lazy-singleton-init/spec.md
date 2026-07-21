## ADDED Requirements

### Requirement: 模块级单例延迟初始化
所有模块级单例（包括 `llm_client`、`vector_store`、`http_client`、`event_cache`、`event_vector_store`）SHALL 采用延迟初始化模式，import 阶段不连接任何外部依赖。

#### Scenario: import 阶段不连接外部依赖
- **WHEN** 执行 `from app.main import app`
- **THEN** Redis 连接 SHALL 未建立
- **AND** ChromaDB 客户端 SHALL 未初始化
- **AND** Embedding 模型 SHALL 未加载
- **AND** 服务 SHALL 能够正常启动

#### Scenario: 第一次使用时自动初始化
- **WHEN** 首次调用 `llm_client.invoke()`
- **THEN** `RedisGate` SHALL 自动初始化
- **AND** Redis 连接 SHALL 建立
- **AND** 后续调用直接复用已初始化的实例

### Requirement: 服务启动健壮性
即使外部依赖（Redis、history-service 等）不可用，服务 SHALL 能够正常启动并响应健康检查请求。

#### Scenario: Redis 不可用时服务仍可启动
- **WHEN** Redis 服务不可用
- **THEN** FastAPI 应用 SHALL 正常启动
- **AND** `/v1/health` 接口 SHALL 正常响应
- **AND** 需要 Redis 的请求 SHALL 返回明确的错误信息

#### Scenario: 向量库不可用时服务仍可启动
- **WHEN** ChromaDB 数据目录损坏或 Embedding 模型加载失败
- **THEN** FastAPI 应用 SHALL 正常启动
- **AND** `/v1/health` 接口 SHALL 正常响应
- **AND** 需要向量库的请求 SHALL 返回明确的错误信息

### Requirement: 启动钩子后台预热
向量存储和事件向量存储 SHALL 在应用启动钩子中以非阻塞方式后台预热，减少第一次请求的延迟。

#### Scenario: 启动后后台预热向量库
- **WHEN** 应用启动完成
- **THEN** 后台 SHALL 自动开始初始化向量存储
- **AND** 不阻塞服务启动
- **AND** 初始化完成后后续请求直接使用
