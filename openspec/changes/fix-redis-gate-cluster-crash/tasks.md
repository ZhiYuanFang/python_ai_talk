## 1. 修复 Redis 闸门集群连接

- [x] 1.1 清理 redis_gate.py 的 import，移除同步 redis，统一使用 redis.asyncio
- [x] 1.2 删除 RedisCluster.from_url() 调用，直接使用手动解析的 startup_nodes 创建集群客户端
- [x] 1.3 将集群客户端改为异步版 redis.asyncio.cluster.RedisCluster
- [ ] 1.4 验证单机模式和集群模式下 acquire、release、get_current_inflight 方法均正常工作

## 2. 实现模块级单例延迟初始化

- [x] 2.1 修改 LLMClient，将 RedisGate 初始化移到第一次调用时（lazy init）
- [x] 2.2 修改 vector_store，实现延迟初始化（首次访问时加载模型和 ChromaDB）
- [x] 2.3 修改 http_client，实现延迟初始化
- [x] 2.4 修改 event_cache，实现延迟初始化
- [x] 2.5 修改 event_vector_store，实现延迟初始化
- [x] 2.6 验证 import 阶段不连接任何外部依赖，服务可正常启动

## 3. 添加启动钩子后台预热

- [x] 3.1 在 main.py 的 startup 事件中添加向量存储后台预热任务
- [x] 3.2 确保预热不阻塞服务启动
- [x] 3.3 预热完成后请求可直接使用已初始化的向量存储

## 4. 修复 Docker 配置

- [x] 4.1 修复 Dockerfile HEALTHCHECK 路径为 /v1/health
- [x] 4.2 将 Dockerfile 中 uvicorn --workers 从 2 改为 1
- [x] 4.3 修复 docker-compose.yml 中的 healthcheck 路径
- [ ] 4.4 构建 Docker 镜像并验证容器正常启动且状态为 healthy

## 5. 验证测试

- [ ] 5.1 本地单机 Redis 模式验证服务启动和所有接口功能
- [ ] 5.2 模拟集群 URL 模式验证 Redis 闸门正常工作
- [ ] 5.3 验证健康检查路径正确返回
- [ ] 5.4 验证 Redis 不可用时服务仍可启动并返回明确错误
