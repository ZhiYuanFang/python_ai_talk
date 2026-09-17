## REMOVED Requirements

### Requirement: 向量数据库构建脚本
**Reason**: 通识 MD → `mother_baby_knowledge` 构建退役；语料与脚本从仓库删除。
**Migration**: 不再执行 `scripts/build_vector_db.py`；意图缓存集合由运行时维护，不依赖该脚本。

### Requirement: 文档切分
**Reason**: 通识构建脚本删除。
**Migration**: 无。

### Requirement: Embedding 模型下载
**Reason**: 就通识构建脚本而言退役；若意图缓存仍用同一 embedding 运行时，由服务既有加载路径负责，不依赖本脚本义务。
**Migration**: 以服务内 embedding 初始化为准。
