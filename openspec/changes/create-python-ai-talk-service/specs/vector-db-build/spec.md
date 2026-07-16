## ADDED Requirements

### Requirement: 向量数据库构建脚本
系统 SHALL 提供向量数据库构建脚本，支持文档切分、embedding、写入 Chroma。

#### Scenario: 执行构建脚本
- **WHEN** 用户执行 `python scripts/build_vector_db.py`
- **THEN** 脚本加载知识库文档，切分后进行 embedding，写入 Chroma 向量库

#### Scenario: 指定数据源目录
- **WHEN** 用户执行 `python scripts/build_vector_db.py --data-dir ./data/knowledge`
- **THEN** 脚本从指定目录加载知识库文档

#### Scenario: 指定输出目录
- **WHEN** 用户执行 `python scripts/build_vector_db.py --output-dir ./data/chroma_db`
- **THEN** 脚本将向量库写入指定目录

### Requirement: 文档切分
系统 SHALL 支持将长文档切分为合适长度的 chunks。

#### Scenario: 切分中文文档
- **WHEN** 脚本处理中文文档
- **THEN** 脚本按句子边界切分文档，每个 chunk 不超过 512 tokens

#### Scenario: 保留上下文
- **WHEN** 脚本切分文档
- **THEN** 相邻 chunks 之间保留一定的重叠内容，保持上下文连贯性

### Requirement: Embedding 模型下载
系统 SHALL 在首次使用时自动下载 BGE-small-zh-v1.5 模型。

#### Scenario: 首次下载模型
- **WHEN** 脚本首次执行且本地无模型文件
- **THEN** 脚本自动下载 BGE-small-zh-v1.5 模型到本地

#### Scenario: 使用本地模型
- **WHEN** 脚本执行且本地已有模型文件
- **THEN** 脚本直接使用本地模型，不再下载

### Requirement: 增量更新
系统 SHALL 支持向量库的增量更新，避免每次全量重建。

#### Scenario: 检测新增文档
- **WHEN** 脚本执行时检测到新增文档
- **THEN** 脚本仅对新增文档进行 embedding 和写入

#### Scenario: 检测更新文档
- **WHEN** 脚本执行时检测到已更新的文档
- **THEN** 脚本删除旧向量，重新 embedding 并写入新向量

### Requirement: 向量库验证
系统 SHALL 在构建完成后验证向量库的完整性。

#### Scenario: 验证向量数量
- **WHEN** 脚本完成构建
- **THEN** 脚本统计向量数量并输出

#### Scenario: 验证检索功能
- **WHEN** 脚本完成构建
- **THEN** 脚本执行一次检索测试，验证检索功能正常