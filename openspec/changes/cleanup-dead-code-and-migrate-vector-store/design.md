## Context

项目经历了 LangGraph 编排重构（`langgraph-orchestration-refactor` change），将图编排逻辑从 `app/graphs/` 迁移到了 `app/clinic/graphs/` 和 `app/feeding/graphs/`，同时将共享服务从 `app/services/` 迁移到了 `app/shared/`。但旧代码未被清理，且 `scripts/build_vector_db.py` 仍引用旧版 `app.services.vector_store`。

当前活跃代码与新旧代码的依赖关系：

```
活跃代码:
  app/shared/vector_store.py     ← 被 main.py、API 路由、clinic/graphs 引用
  app/clinic/graphs/             ← 被 API 路由引用
  app/feeding/graphs/            ← 被 API 路由引用

死代码:
  app/services/                  ← 仅被 app/graphs/ 和 build_vector_db.py 引用
  app/graphs/                    ← 仅内部互相引用，无外部 import
  app/schemas/                   ← 仅内部互相引用
  app/clinic/services/knowledge_vector_store.py  ← 无任何引用
```

## Goals / Non-Goals

**Goals:**
- 删除所有死代码，减少混淆和内存浪费
- 将 `build_vector_db.py` 迁移到使用新版 `app.shared.vector_store`，使构建的知识库自动包含扩展元数据字段
- 确保删除后项目可正常启动和运行

**Non-Goals:**
- 不修改 `app/shared/vector_store.py` 的功能逻辑
- 不修改 `app/clinic/graphs/` 或 `app/feeding/graphs/` 的图编排逻辑
- 不处理 Docker 挂载卷模型覆盖问题（单独处理）

## Decisions

### 决策 1：先迁移 import，再删除旧代码

**选择**：先修改 `build_vector_db.py` 和 `docs/vector_db_guide.md` 的 import 引用，再删除旧代码目录。

**理由**：如果先删除旧代码，`build_vector_db.py` 会立即报 ImportError，导致服务启动失败（main.py 的 startup_event 会调用 build_vector_db）。

**替代方案**：先删除再修复 — 被否决，因为会导致中间状态不可运行。

### 决策 2：新版 VectorStore 的兼容性

**选择**：直接迁移 import，无需修改 `build_vector_db.py` 的调用逻辑。

**理由**：新版 `app.shared.vector_store.VectorStore` 的 `add_documents`、`search`、`clear`、`get_document_count`、`rebuild` 方法签名与旧版完全兼容。新版 `add_documents` 的改进（自动生成 UUID、添加扩展元数据默认值）是增量式的，不会破坏旧调用方。

关键差异对照：
- 旧版 `add_documents` 生成 `doc_0`, `doc_1` ID → 新版生成 UUID，但 build_vector_db.py 不依赖 ID 格式
- 旧版 `search` 不返回 `id` 字段 → 新版返回 `id`，build_vector_db.py 的验证逻辑不读取 `id`
- 旧版无扩展元数据 → 新版自动添加 `quality_score=0.8`、`match_count=0` 等默认值，这正是我们想要的

### 决策 3：删除范围

**选择**：删除 `app/services/`、`app/graphs/`、`app/schemas/`、`app/clinic/services/knowledge_vector_store.py`。

**理由**：通过全项目 grep 验证，这些目录和文件仅被自身内部引用或无任何引用。活跃代码已全部使用 `app/shared/*`、`app/clinic/graphs/*`、`app/feeding/graphs/*`。

## Risks / Trade-offs

- **[风险] 遗漏隐藏引用** → 通过全项目 grep `from app.services.`、`from app.graphs.`、`from app.schemas.` 验证，确认仅 build_vector_db.py 和 docs 引用旧代码
- **[风险] build_vector_db.py 行为变化** → 新版 add_documents 生成 UUID 而非 doc_0/doc_1，但验证逻辑不依赖 ID 格式，且新版自动添加扩展元数据是期望行为
- **[回滚]** → 如果删除后发现遗漏引用，可通过 git 恢复删除的文件
