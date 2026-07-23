## Context

项目使用 ChromaDB 作为向量数据库，`pyproject.toml` 中指定依赖为 `chromadb = "^0.4.24"`。在本地运行 `python -m scripts.build_vector_db` 时遇到 API 兼容性问题：

- **错误信息**：`Expected include item to be one of embeddings, documents, metadatas, uris, data, distances, got ids`
- **根因**：ChromaDB 0.5.x+ 版本对 API 做了破坏性变更，`query()` 和 `get()` 方法的 `include` 参数不再接受 `"ids"` 作为选项
- **当前行为**：新版本 ChromaDB 始终默认返回 `ids`，无需显式指定
- **受影响文件**：
  - `app/shared/vector_store.py`：5 处 `include` 包含 `"ids"`
  - `app/feeding/services/event_vector_store.py`：需检查是否存在同类问题

## Goals / Non-Goals

**Goals:**
- 修复 ChromaDB 0.5.x+ 版本下 `include` 参数报错的问题
- 确保向量数据库构建脚本可正常运行
- 确保所有向量库操作（query、get、add、update、delete）功能正常
- 保持对 ChromaDB 0.4.x 的向后兼容

**Non-Goals:**
- 不升级或降级 ChromaDB 版本
- 不改变向量库的业务逻辑（仅修复 API 调用参数）
- 不重构向量存储模块架构

## Decisions

### 决策 1：从 include 参数中移除 "ids"

**选择**：将所有 `include=[..., "ids"]` 修改为 `include=[...]`，移除 `"ids"` 选项

**理由**：
- ChromaDB 0.5.x+ 中 `"ids"` 已从 `include` 允许列表中移除
- 新版本 ChromaDB 始终默认返回 `ids`，无需显式请求
- 此修改对 0.4.x 也兼容——即使不显式指定 `"ids"`，旧版本也会默认返回

**备选方案**：
- 方案 A：升级/降级 chromadb 到特定版本 → 否决，改动风险大，影响面广
- 方案 B：封装一层兼容层，根据版本动态调整 include → 否决，过度设计，简单问题复杂化

### 决策 2：不修改 pyproject.toml 中的 chromadb 版本约束

**选择**：保持 `chromadb = "^0.4.24"` 不变

**理由**：
- 修复后代码同时兼容 0.4.x 和 0.5.x+
- 不强制用户升级或降级，保持灵活性
- 生产环境使用 Docker 镜像构建，依赖版本锁定，不受本地安装版本影响

## Risks / Trade-offs

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 遗漏某些 include 中的 "ids" | 部分功能仍报错 | 全局 grep 搜索 `include.*ids` 确保全部覆盖 |
| ChromaDB 未来版本有更多 API 变更 | 再次出现兼容性问题 | 关注 ChromaDB 发行说明，考虑在 CI 中添加版本锁定 |
| 旧数据（0.4.x 创建）与新版本不兼容 | 向量库数据无法读取 | ChromaDB 向后兼容数据格式；如有问题可删除后重建 |

**无破坏性变更**：本次修改仅调整参数传递方式，不改变任何返回数据结构，不影响业务逻辑。

## Migration Plan

1. 修改代码：从所有 `include=[...]` 中移除 `"ids"`
2. 本地验证：运行 `python -m scripts.build_vector_db` 确认构建成功
3. 功能验证：执行检索测试确认查询功能正常
4. 回滚方案：如遇问题，恢复修改即可（改动量极小，5 行以内）
