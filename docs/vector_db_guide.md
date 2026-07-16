# 向量数据库完全指南

> **作者**: AI Talk 团队
> **版本**: v1.0
> **日期**: 2026年7月

---

## 目录

1. [什么是向量数据库](#1-什么是向量数据库)
   - 1.1 传统数据库的局限
   - 1.2 向量数据库的优势
   - 1.3 向量数据库的应用场景

2. [什么是 Embedding](#2-什么是-embedding)
   - 2.1 文本如何转换为向量
   - 2.2 Embedding 模型介绍
   - 2.3 BGE-small-zh-v1.5 模型特点

3. [Chroma 向量数据库](#3-chroma-向量数据库)
   - 3.1 Chroma 简介
   - 3.2 Chroma 核心概念
   - 3.3 Chroma 的使用场景

4. [环境准备](#4-环境准备)
   - 4.1 Python 安装
   - 4.2 依赖安装
   - 4.3 模型下载

5. [知识库准备](#5-知识库准备)
   - 5.1 文档格式要求
   - 5.2 目录结构
   - 5.3 示例文档

6. [向量库构建](#6-向量库构建)
   - 6.1 构建脚本使用
   - 6.2 构建过程详解
   - 6.3 结果验证

7. [向量库使用](#7-向量库使用)
   - 7.1 基本检索操作
   - 7.2 参数说明
   - 7.3 结果解析

8. [向量库维护](#8-向量库维护)
   - 8.1 增量更新
   - 8.2 全量重建
   - 8.3 备份与恢复

9. [常见问题解答](#9-常见问题解答)

---

## 1. 什么是向量数据库

### 1.1 传统数据库的局限

传统数据库（如 MySQL、PostgreSQL）使用结构化数据和精确匹配进行查询。例如：

```sql
-- 查询名字叫"张三"的用户
SELECT * FROM users WHERE name = '张三';
```

这种方式在处理以下场景时非常困难：

- **语义相似性查询**：用户问"宝宝拉肚子怎么办"，传统数据库无法找到"婴儿腹泻处理方法"这样语义相似的内容
- **模糊查询**：用户输入有拼写错误或用词不同
- **多模态数据**：图片、语音、视频等非结构化数据

### 1.2 向量数据库的优势

向量数据库将数据转换为高维向量（Embedding），通过计算向量之间的相似度来进行检索。

**核心思想**：
1. 将文本、图片等数据转换为向量（Embedding）
2. 存储这些向量
3. 查询时，将查询词也转换为向量，找到最相似的向量

**相似度计算**：
- **余弦相似度**：衡量两个向量方向的相似程度，范围 [-1, 1]
- **欧氏距离**：衡量两个向量之间的直线距离，值越小越相似

### 1.3 向量数据库的应用场景

| 场景 | 示例 |
|------|------|
| **语义搜索** | 用户问"宝宝拉肚子怎么办"，找到相关的育儿知识 |
| **推荐系统** | 根据用户兴趣推荐相似内容 |
| **问答系统** | 从知识库中找到最相关的答案 |
| **图片搜索** | 根据图片内容搜索相似图片 |
| **代码搜索** | 根据自然语言描述搜索代码 |

---

## 2. 什么是 Embedding

### 2.1 文本如何转换为向量

Embedding 是将文本、图片、音频等数据转换为数值向量的过程。

**示例**：

```
输入文本："宝宝拉肚子怎么办"

输出向量：[0.123, -0.456, 0.789, ..., 0.321]
         (通常是 768 或 384 维的浮点数数组)
```

**转换过程**：
1. 将文本分词（如中文分词为"宝宝"、"拉肚子"、"怎么办"）
2. 查找每个词的词向量
3. 通过模型计算得到最终的句子向量

### 2.2 Embedding 模型介绍

常用的 Embedding 模型：

| 模型 | 特点 | 适用场景 |
|------|------|----------|
| **BGE-small-zh-v1.5** | 中文效果好，体积小（~90MB），免费 | 中文语义搜索 |
| **text-embedding-3-small** | OpenAI 出品，多语言支持 | 需要付费 API |
| **m3e-base** | 中文开源模型，效果优秀 | 中文语义搜索 |
| **sentence-transformers/all-MiniLM-L6-v2** | 英文模型，体积小 | 英文语义搜索 |

### 2.3 BGE-small-zh-v1.5 模型特点

**优点**：
- **中文效果优秀**：专门针对中文训练，理解中文语义更好
- **体积小**：只有约 90MB，下载和加载速度快
- **免费开源**：可以在本地部署，不需要付费 API
- **速度快**：在 CPU 上也能快速处理

**适用场景**：
- 中文语义搜索
- 中文问答系统
- 中文推荐系统

---

## 3. Chroma 向量数据库

### 3.1 Chroma 简介

Chroma 是一个开源的向量数据库，专为 AI 应用设计。

**主要特点**：
- **零部署**：不需要单独部署服务，直接作为 Python 库使用
- **开箱即用**：几行代码即可创建和使用向量数据库
- **持久化存储**：支持将数据保存到本地文件系统
- **内置 Embedding**：支持多种 Embedding 模型

### 3.2 Chroma 核心概念

| 概念 | 说明 |
|------|------|
| **Collection** | 向量集合，类似于数据库中的表 |
| **Document** | 原始文本内容 |
| **Embedding** | 文本转换后的向量 |
| **Metadata** | 文档的元数据（如分类、标签等） |
| **ID** | 文档的唯一标识符 |

**数据流程**：
```
原始文档 → Embedding → 向量存储 → 查询向量 → 相似度计算 → 返回结果
```

### 3.3 Chroma 的使用场景

- **本地开发**：不需要服务器，直接在本地使用
- **小型应用**：数据量不大（百万级以下）的应用
- **AI 应用**：需要语义搜索的 AI 应用

---

## 4. 环境准备

### 4.1 Python 安装

**Windows**：
1. 访问 [Python 官网](https://www.python.org/downloads/)
2. 下载 Python 3.11 或更高版本
3. 安装时勾选 "Add Python to PATH"

**验证安装**：
```bash
python --version
# 输出：Python 3.11.x
```

### 4.2 依赖安装

使用 Poetry 安装项目依赖：

```bash
# 进入项目目录
cd python_ai_talk

# 安装依赖
poetry install

# 激活虚拟环境
poetry shell
```

**核心依赖说明**：

| 依赖 | 作用 |
|------|------|
| **chromadb** | 向量数据库 |
| **sentence-transformers** | Embedding 模型加载 |
| **BAAI/bge-small-zh-v1.5** | 中文 Embedding 模型 |
| **fastapi** | Web 服务框架 |
| **httpx** | HTTP 客户端 |

### 4.3 模型下载

首次运行时，BGE-small-zh-v1.5 模型会自动下载：

```bash
# 运行构建脚本，会自动下载模型
python scripts/build_vector_db.py
```

**模型存储位置**：
```
python_ai_talk/data/models/
└── sentence-transformers_BAAI-bge-small-zh-v1.5/
    ├── config.json
    ├── pytorch_model.bin
    ├── tokenizer.json
    └── ...
```

**手动下载（如果自动下载失败）**：
1. 访问 [Hugging Face](https://huggingface.co/BAAI/bge-small-zh-v1.5)
2. 下载所有文件
3. 放入 `data/models/sentence-transformers_BAAI-bge-small-zh-v1.5/` 目录

---

## 5. 知识库准备

### 5.1 文档格式要求

**支持的格式**：
- **Markdown**（.md）：推荐使用，支持标题、列表等格式
- **TXT**（.txt）：纯文本格式

**文档内容要求**：
- 编码格式：UTF-8
- 内容语言：中文
- 建议长度：每个文档 500-5000 字

**示例文档结构**：
```markdown
# 宝宝腹泻处理指南

## 什么是腹泻

腹泻是指宝宝每天排便次数增多，大便性状改变。

## 处理方法

1. 补充水分，防止脱水
2. 清淡饮食，避免油腻
3. 观察病情变化

## 注意事项

如果出现以下情况，请及时就医：
- 腹泻持续超过 3 天
- 出现脱水症状
- 大便带血
```

### 5.2 目录结构

```
python_ai_talk/data/knowledge/
├── 喂养知识/
│   ├── 母乳喂养.md
│   ├── 奶粉喂养.md
│   └── 辅食添加.md
├── 健康护理/
│   ├── 腹泻处理.md
│   ├── 发烧护理.md
│   └── 睡眠问题.md
└── 生长发育/
    ├── 身高体重.md
    └── 发育里程碑.md
```

**目录说明**：
- 根目录：`data/knowledge/`
- 子目录：按主题分类（如"喂养知识"、"健康护理"）
- 文件：每个文件对应一个知识主题

### 5.3 示例文档

**data/knowledge/健康护理/腹泻处理.md**：

```markdown
# 宝宝腹泻处理指南

## 什么是腹泻

腹泻是指宝宝每天排便次数明显增多，大便性状改变（如稀水样、蛋花汤样）。

## 常见原因

1. **感染性腹泻**：病毒或细菌感染
2. **消化不良**：喂养不当或腹部受凉
3. **食物过敏**：对某些食物过敏

## 家庭处理方法

### 补充水分
- 多喝温水或口服补液盐
- 少量多次饮用

### 调整饮食
- 母乳喂养：继续母乳喂养
- 奶粉喂养：可暂时更换为无乳糖奶粉
- 辅食：暂停新辅食，清淡饮食

### 观察症状
- 记录排便次数和性状
- 观察精神状态和尿量

## 就医指征

出现以下情况，请及时就医：

- 腹泻持续超过 3 天
- 出现脱水症状（尿量减少、口唇干燥、精神萎靡）
- 大便带血或黏液
- 发烧超过 38.5℃
- 呕吐频繁

## 预防措施

- 注意饮食卫生
- 勤洗手
- 避免腹部受凉
```

---

## 6. 向量库构建

### 6.1 构建脚本使用

**基本用法**：
```bash
# 进入项目目录
cd python_ai_talk

# 激活虚拟环境
poetry shell

# 运行构建脚本
python scripts/build_vector_db.py
```

**指定参数**：
```bash
# 指定数据源目录
python scripts/build_vector_db.py --data-dir ./data/knowledge

# 指定输出目录
python scripts/build_vector_db.py --output-dir ./data/chroma_db

# 强制全量重建
python scripts/build_vector_db.py --force
```

### 6.2 构建过程详解

**构建流程**：

```
步骤 1: 加载文档
        ↓
步骤 2: 切分文档（按句子边界，每个 chunk ≤ 512 tokens）
        ↓
步骤 3: Embedding（使用 BGE-small-zh-v1.5 转换为向量）
        ↓
步骤 4: 写入 Chroma（将向量和元数据存储）
        ↓
步骤 5: 验证（检查文档数量和检索功能）
```

**详细说明**：

1. **文档加载**：遍历 `data/knowledge/` 目录，读取所有 .md 和 .txt 文件

2. **文档切分**：
   - 按句子边界切分（。！？；\n\n）
   - 每个 chunk 不超过 512 tokens
   - 相邻 chunks 保留 100 字符重叠，保持上下文连贯

3. **Embedding**：
   - 使用 BGE-small-zh-v1.5 模型
   - 将文本转换为 384 维向量
   - 第一次运行需要下载模型（约 90MB）

4. **写入 Chroma**：
   - 创建或获取 Collection：`mother_baby_knowledge`
   - 存储向量、文档内容和元数据

5. **验证**：
   - 检查向量库中的文档数量
   - 执行检索测试

### 6.3 结果验证

**验证日志示例**：

```
开始构建向量数据库
数据源目录: ./data/knowledge
输出目录: ./data/chroma_db
强制重建: False

步骤 1: 加载文档...
共加载 10 个文档

步骤 2: 切分文档...
切分文档: 100%|██████████| 10/10 [00:01<00:00,  8.50it/s]
共生成 50 个 chunks

步骤 3: 写入向量库...
开始对 50 个文档进行 Embedding...
开始将 50 个文档写入向量库...
成功添加 50 个文档到向量库

步骤 4: 验证构建结果...
验证通过！向量库中共有 50 个文档

执行检索测试...
检索测试成功！找到 3 个相关文档
  1. 相似度: 0.9234, 内容预览: 宝宝腹泻处理指南...
  2. 相似度: 0.8567, 内容预览: 发烧护理方法...
  3. 相似度: 0.7890, 内容预览: 消化不良处理...

向量数据库构建完成！
```

---

## 7. 向量库使用

### 7.1 基本检索操作

**Python 代码示例**：

```python
# 导入向量存储服务
from app.services.vector_store import vector_store

# 执行检索
results = vector_store.search(
    query="宝宝拉肚子怎么办",
    n_results=5
)

# 处理结果
for result in results:
    print(f"相似度: {result['score']}")
    print(f"内容: {result['content']}")
    print(f"分类: {result['metadata']['category']}")
    print("-" * 50)
```

### 7.2 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| **query** | str | - | 查询文本，必填 |
| **n_results** | int | 5 | 返回结果数量 |

### 7.3 结果解析

**返回结果格式**：

```python
[
    {
        "content": "宝宝腹泻处理指南...",  # 文档内容
        "metadata": {                    # 元数据
            "file_name": "腹泻处理.md",
            "category": "健康护理",
            "chunk_index": 0,
            "total_chunks": 3
        },
        "score": 0.9234                  # 相似度分数（0-1，越大越相似）
    },
    # ... 更多结果
]
```

**相似度分数说明**：
- **0.9 以上**：非常相关
- **0.7-0.9**：比较相关
- **0.5-0.7**：一般相关
- **0.5 以下**：不太相关

---

## 8. 向量库维护

### 8.1 增量更新

**自动检测**：
构建脚本会自动检测新增和更新的文档：

```bash
# 直接运行构建脚本，会增量更新
python scripts/build_vector_db.py
```

**原理**：
- 脚本会对比本地文档和向量库中的文档
- 只对新增或修改过的文档进行 Embedding
- 不需要全量重建

### 8.2 全量重建

**场景**：
- 知识库结构发生重大变化
- 向量库数据损坏
- 需要重新调整 chunk 大小

**操作**：
```bash
# 使用 --force 参数强制全量重建
python scripts/build_vector_db.py --force
```

**流程**：
1. 清空现有向量库
2. 重新加载所有文档
3. 重新切分和 Embedding
4. 重新写入向量库

### 8.3 备份与恢复

**备份**：
```bash
# 复制向量库数据目录
cp -r data/chroma_db backup/chroma_db_$(date +%Y%m%d)
```

**恢复**：
```bash
# 恢复向量库数据
cp -r backup/chroma_db_20260715 data/chroma_db
```

**注意事项**：
- 备份时确保服务已停止
- 恢复时使用相同版本的 Chroma
- 定期备份，防止数据丢失

---

## 9. 常见问题解答

### Q1: 模型下载失败怎么办？

**原因**：网络问题或 Hugging Face 访问受限

**解决方案**：
1. **手动下载**：
   - 访问 [BGE-small-zh-v1.5](https://huggingface.co/BAAI/bge-small-zh-v1.5)
   - 下载所有文件
   - 放入 `data/models/sentence-transformers_BAAI-bge-small-zh-v1.5/` 目录

2. **使用代理**：
   ```bash
   export http_proxy=http://your-proxy:port
   export https_proxy=http://your-proxy:port
   python scripts/build_vector_db.py
   ```

### Q2: 构建速度慢怎么办？

**原因**：文档数量多或 CPU 性能不足

**解决方案**：
1. **使用 GPU**（如果有）：
   - 安装 CUDA 和 PyTorch GPU 版本
   - Embedding 速度会大幅提升

2. **分批构建**：
   - 将知识库分成多个目录
   - 分批运行构建脚本

3. **减少文档数量**：
   - 只保留最相关的知识
   - 合并相似的文档

### Q3: 检索结果不准确怎么办？

**原因**：文档质量差或检索参数不合适

**解决方案**：
1. **优化文档内容**：
   - 确保文档内容准确、完整
   - 使用清晰的标题和结构

2. **调整检索参数**：
   ```python
   # 增加返回数量，查看更多结果
   results = vector_store.search(query, n_results=10)
   ```

3. **增加文档数量**：
   - 添加更多相关文档
   - 覆盖更多知识领域

### Q4: 向量库占用空间太大怎么办？

**原因**：文档数量多或 Embedding 维度高

**解决方案**：
1. **清理旧数据**：
   ```bash
   # 删除不需要的文档后重建
   python scripts/build_vector_db.py --force
   ```

2. **使用更小的模型**：
   - BGE-small-zh-v1.5 已经是较小的模型
   - 如需更小，可考虑 BGE-micro（约 30MB）

### Q5: 如何更新知识库？

**步骤**：
1. 在 `data/knowledge/` 目录中添加或修改文档
2. 运行构建脚本：
   ```bash
   python scripts/build_vector_db.py
   ```
3. 脚本会自动检测并增量更新

---

## 附录

### A. 常用命令

```bash
# 构建向量库
python scripts/build_vector_db.py

# 强制全量重建
python scripts/build_vector_db.py --force

# 指定数据源目录
python scripts/build_vector_db.py --data-dir ./data/knowledge

# 查看向量库文档数量
python -c "from app.services.vector_store import vector_store; print(vector_store.get_document_count())"

# 测试检索功能
python -c "from app.services.vector_store import vector_store; print(vector_store.search('宝宝拉肚子怎么办'))"
```

### B. 目录结构

```
python_ai_talk/
├── app/                      # 应用代码
│   ├── api/                  # API 路由
│   ├── services/             # 服务层
│   │   └── vector_store.py   # 向量存储服务
│   └── ...
├── data/
│   ├── chroma_db/            # 向量库数据（自动生成）
│   ├── knowledge/            # 知识库文档（需要手动添加）
│   │   ├── 喂养知识/
│   │   ├── 健康护理/
│   │   └── 生长发育/
│   └── models/               # Embedding 模型（自动下载）
├── scripts/
│   └── build_vector_db.py    # 向量库构建脚本
└── docs/
    └── vector_db_guide.md    # 本指南
```

### C. 参考资源

- [Chroma 官方文档](https://docs.trychroma.com/)
- [BGE-small-zh-v1.5 模型](https://huggingface.co/BAAI/bge-small-zh-v1.5)
- [sentence-transformers 文档](https://www.sbert.net/)

---

**恭喜！你已经学会了向量数据库的使用！** 🎉

如果还有其他问题，请随时联系 AI Talk 团队。