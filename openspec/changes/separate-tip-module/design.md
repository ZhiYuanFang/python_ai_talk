## Context

当前项目有三个业务模块：feeding、clinic、tip。其中 feeding 和 clinic 各有独立的目录，但 tip 模块嵌套在 `app/clinic/` 下，与 clinic 代码混放。

当前代码组织的问题：
1. tip 相关文件（tip_graph.py、tip_state.py、tip.py）散落在 `app/clinic/` 下的多个子目录中
2. tip 和 clinic 共享的 4 个数据准备节点（fetch_history、search_vectors、fetch_baby_profile、judge_data_requirement）放在 `app/clinic/graphs/nodes/` 下，但它们不属于 clinic，应该属于共享层
3. 三个业务模块组织方式不统一（feeding 独立、clinic 独立、tip 嵌套）

## Goals / Non-Goals

**Goals:**
- 将 tip 模块从 `app/clinic/` 中拆分出来，建立独立的 `app/tip/` 目录，与 feeding、clinic 保持一致的组织方式
- 将 tip 和 clinic 共享的图节点移动到 `app/shared/graphs/nodes/` 共享层
- 更新所有受影响的 import 路径
- 确保所有功能在重构后完全不变

**Non-Goals:**
- 不改变任何业务逻辑
- 不修改任何 API 接口
- 不修改任何数据结构
- 不改变任何依赖版本
- 不添加新功能

## Decisions

### 决策 1：tip 模块目录结构与 feeding 保持一致

**决定**：`app/tip/` 的目录结构完全对齐 `app/feeding/` 的组织方式：
```
app/tip/
├── graphs/
│   ├── nodes/
│   │   └── stream_tip_response.py
│   ├── states/
│   │   └── tip_state.py
│   └── tip_graph.py
├── schemas/
│   └── tip.py
└── __init__.py
```

**理由**：
- 与 feeding 模块结构一致，降低认知成本
- 便于后续维护和扩展

**备选方案**：自定义一套不同的目录结构 → 放弃，因为统一结构更重要

### 决策 2：共享图节点放在 `app/shared/graphs/nodes/`

**决定**：将 fetch_history、search_vectors、fetch_baby_profile、judge_data_requirement 这 4 个被 tip 和 clinic 共享的节点移动到 `app/shared/graphs/nodes/` 目录。

**理由**：
- 这些节点不属于任何一个业务模块，它们是通用的数据准备步骤
- 放在 shared/ 下语义正确，且与项目中其他共享组件（llm_client、vector_store、http_client 等）的组织方式一致
- 避免未来有新业务模块时重复移动

**备选方案**：保持节点在 clinic 下，tip 通过长路径引用 → 放弃，因为语义不正确，且 clinic 目录不应包含被其他模块使用的共享代码

### 决策 3：移动文件而非复制

**决定**：直接移动文件到新位置，并同步更新所有 import 路径。不保留旧文件的副本。

**理由**：
- 避免代码重复
- 单一职责原则，每个文件只在一个位置存在

**备选方案**：先复制再逐步替换 → 放弃，因为本次变更范围明确，一次性完成更清晰

## Risks / Trade-offs

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| import 路径遗漏更新导致 ImportError | 服务启动失败 | 全局搜索旧路径，确保所有引用都更新；启动后完整测试所有接口 |
| 移动文件后 __init__.py 缺失导致模块不可导入 | 服务启动失败 | 所有新建目录都添加 __init__.py |
| 共享节点移动后，原来在 clinic 下的相对引用失效 | 节点执行出错 | 逐个检查共享节点内部的 import 路径 |
