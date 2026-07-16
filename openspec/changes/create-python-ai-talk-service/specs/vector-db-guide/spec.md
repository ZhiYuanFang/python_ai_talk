## ADDED Requirements

### Requirement: 向量数据库概念教学文档
系统 SHALL 提供向量数据库完整教学文档，从基础概念到实际使用的详细说明，适合零基础用户阅读。

#### Scenario: 零基础用户理解向量数据库
- **WHEN** 用户阅读教学文档第一章
- **THEN** 用户理解什么是向量数据库、为什么需要向量数据库、向量数据库与传统数据库的区别

#### Scenario: 理解 Embedding 概念
- **WHEN** 用户阅读教学文档第二章
- **THEN** 用户理解什么是 Embedding、Embedding 如何将文本转换为向量、BGE-small-zh-v1.5 模型的特点

#### Scenario: 理解 Chroma 向量数据库
- **WHEN** 用户阅读教学文档第三章
- **THEN** 用户理解 Chroma 是什么、Chroma 的核心概念（Collection、Embedding、Query）、Chroma 的使用场景

### Requirement: 环境准备教学
系统 SHALL 在教学文档中详细说明如何准备向量数据库运行环境。

#### Scenario: Python 环境安装
- **WHEN** 用户按照文档操作
- **THEN** 用户成功安装 Python 3.11+ 和必要的依赖包

#### Scenario: 依赖包安装
- **WHEN** 用户执行 `pip install chromadb sentence-transformers`
- **THEN** 用户成功安装 Chroma 和 BGE-small-zh-v1.5 相关依赖

#### Scenario: 模型下载说明
- **WHEN** 用户首次运行构建脚本
- **THEN** 用户理解 BGE-small-zh-v1.5 模型会自动下载到本地

### Requirement: 知识库准备教学
系统 SHALL 在教学文档中详细说明如何准备知识库文档。

#### Scenario: 文档格式说明
- **WHEN** 用户阅读文档格式说明
- **THEN** 用户理解支持的文档格式（Markdown、TXT）、文档命名规范、文档内容要求

#### Scenario: 知识库目录结构
- **WHEN** 用户查看知识库目录结构说明
- **THEN** 用户理解如何组织知识库文件（按主题分类、子目录结构）

#### Scenario: 示例文档提供
- **WHEN** 用户查看示例文档
- **THEN** 用户理解文档内容应包含哪些要素（问题、答案、注意事项等）

### Requirement: 向量库构建教学
系统 SHALL 在教学文档中详细说明如何构建向量数据库。

#### Scenario: 执行构建脚本
- **WHEN** 用户执行 `python scripts/build_vector_db.py`
- **THEN** 用户成功构建向量数据库，且理解每个步骤的作用

#### Scenario: 构建过程日志
- **WHEN** 用户执行构建脚本
- **THEN** 用户通过日志了解构建进度（文档加载、切分、Embedding、写入）

#### Scenario: 构建结果验证
- **WHEN** 用户执行验证命令
- **THEN** 用户确认向量数据库构建成功，包含预期数量的向量

### Requirement: 向量库使用教学
系统 SHALL 在教学文档中详细说明如何使用向量数据库进行检索。

#### Scenario: 基本检索操作
- **WHEN** 用户按照文档示例代码操作
- **THEN** 用户成功从向量数据库中检索到相关知识

#### Scenario: 检索参数说明
- **WHEN** 用户阅读检索参数说明
- **THEN** 用户理解 n_results（返回数量）、where（过滤条件）等参数的作用

#### Scenario: 检索结果解析
- **WHEN** 用户查看检索结果
- **THEN** 用户理解结果包含的内容（文档内容、相似度分数、元数据）

### Requirement: 向量库维护教学
系统 SHALL 在教学文档中详细说明如何维护向量数据库。

#### Scenario: 增量更新
- **WHEN** 用户新增知识库文档后重新执行构建脚本
- **THEN** 用户成功实现向量库的增量更新

#### Scenario: 全量重建
- **WHEN** 用户需要全量重建向量库
- **THEN** 用户理解如何删除旧数据并重新构建

#### Scenario: 备份与恢复
- **WHEN** 用户阅读备份恢复说明
- **THEN** 用户理解如何备份 Chroma 数据目录、如何从备份恢复

### Requirement: 常见问题解答
系统 SHALL 在教学文档中提供常见问题解答，帮助用户解决使用过程中遇到的问题。

#### Scenario: 模型下载失败
- **WHEN** 用户遇到模型下载失败问题
- **THEN** 用户在 FAQ 中找到解决方案（更换下载源、手动下载等）

#### Scenario: 构建速度慢
- **WHEN** 用户遇到构建速度慢问题
- **THEN** 用户在 FAQ 中找到优化建议（使用 GPU、减少文档数量等）

#### Scenario: 检索结果不准确
- **WHEN** 用户遇到检索结果不准确问题
- **THEN** 用户在 FAQ 中找到优化建议（调整 n_results、优化文档内容等）

### Requirement: 代码注释规范
系统 SHALL 在所有代码文件中添加详细的中文业务逻辑注释，方便用户跟踪解读。

#### Scenario: 构建脚本注释
- **WHEN** 用户阅读 `scripts/build_vector_db.py`
- **THEN** 用户通过注释理解每个函数、每个步骤的业务逻辑

#### Scenario: 向量存储服务注释
- **WHEN** 用户阅读 `app/services/vector_store.py`
- **THEN** 用户通过注释理解向量存储的初始化、检索、更新等操作的业务逻辑

#### Scenario: API 接口注释
- **WHEN** 用户阅读 `app/api/routes.py`
- **THEN** 用户通过注释理解每个接口的功能、输入输出、业务流程