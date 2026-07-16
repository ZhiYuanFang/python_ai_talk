"""
向量存储服务模块

业务说明：
本模块负责封装 Chroma 向量数据库的操作，提供文档检索能力。
使用 BGE-small-zh-v1.5 作为 Embedding 模型，将文本转换为向量。

设计思路：
1. 使用 Chroma 作为本地向量数据库，支持持久化存储
2. 使用 sentence-transformers 加载 BGE-small-zh-v1.5 模型
3. 封装检索、添加、更新等常用操作
4. 提供单例模式，确保全局只有一个向量存储实例
"""

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from app.config.settings import settings

# 初始化日志记录器
logger = logging.getLogger(__name__)


class VectorStore:
    """
    向量存储服务类

    业务说明：
    提供向量数据库的检索和管理能力，用于母婴知识检索场景。
    支持将文档转换为向量并存储，以及根据查询向量检索相似文档。
    """

    _instance: Optional["VectorStore"] = None  # 单例实例

    def __new__(cls, *args, **kwargs):
        """
        单例模式：确保全局只有一个向量存储实例

        业务逻辑：
        如果实例已存在，直接返回；否则创建新实例
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        """
        初始化向量存储服务

        业务逻辑：
        1. 加载 BGE-small-zh-v1.5 Embedding 模型
        2. 初始化 Chroma 客户端
        3. 创建或获取母婴知识 Collection
        """
        # 防止重复初始化
        if hasattr(self, '_initialized'):
            return

        # 记录初始化开始日志
        logger.info("开始初始化向量存储服务...")

        # 创建数据目录（如果不存在）
        os.makedirs(settings.chroma_persist_dir, exist_ok=True)

        # 加载 Embedding 模型
        # BGE-small-zh-v1.5 是一个轻量级的中文 Embedding 模型，效果好且体积小
        logger.info(f"加载 Embedding 模型: {settings.embedding_model}")
        self._embedding_model = SentenceTransformer(
            settings.embedding_model,
            cache_folder=os.path.join("data", "models"),  # 模型缓存目录
        )

        # 初始化 Chroma 客户端
        # 使用本地文件系统存储，支持持久化
        logger.info(f"初始化 Chroma 客户端，数据目录: {settings.chroma_persist_dir}")
        self._chroma_client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=Settings(
                anonymized_telemetry=False,  # 禁用匿名遥测
                allow_reset=False,  # 禁止重置
            ),
        )

        # 创建或获取母婴知识 Collection
        # Collection 是 Chroma 中存储向量数据的基本单位
        self._collection = self._chroma_client.get_or_create_collection(
            name="mother_baby_knowledge",  # Collection 名称
            metadata={"description": "母婴喂养知识向量库"},  # 描述信息
        )

        # 标记初始化完成
        self._initialized = True

        # 记录初始化完成日志
        logger.info("向量存储服务初始化完成")

    def _embed(self, texts: List[str]) -> List[List[float]]:
        """
        将文本转换为向量

        业务逻辑：
        使用 BGE-small-zh-v1.5 模型将文本列表转换为向量列表

        Args:
            texts: 文本列表

        Returns:
            向量列表，每个向量是一个浮点数列表
        """
        # 使用模型编码文本，转换为向量
        embeddings = self._embedding_model.encode(texts)
        # 将 numpy 数组转换为 Python 列表
        return embeddings.tolist()

    def add_documents(self, documents: List[Dict[str, Any]]):
        """
        添加文档到向量库

        业务逻辑：
        1. 提取文档内容和元数据
        2. 将文档内容转换为向量
        3. 将向量和元数据写入 Chroma

        Args:
            documents: 文档列表，每个文档包含 "content" 和 "metadata" 字段
        """
        if not documents:
            logger.warning("尝试添加空文档列表")
            return

        # 提取文档内容、ID 和元数据
        ids = []
        contents = []
        metadatas = []

        for i, doc in enumerate(documents):
            # 生成文档 ID，格式为 "doc_{index}"
            ids.append(f"doc_{i}")
            # 获取文档内容
            contents.append(doc.get("content", ""))
            # 获取文档元数据
            metadatas.append(doc.get("metadata", {}))

        # 将文档内容转换为向量
        logger.info(f"开始对 {len(documents)} 个文档进行 Embedding...")
        embeddings = self._embed(contents)

        # 将向量和元数据写入 Chroma
        logger.info(f"开始将 {len(documents)} 个文档写入向量库...")
        self._collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=contents,
            metadatas=metadatas,
        )

        # 记录添加完成日志
        logger.info(f"成功添加 {len(documents)} 个文档到向量库")

    def search(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """
        检索相似文档

        业务逻辑：
        1. 将查询文本转换为向量
        2. 在 Chroma 中检索相似向量
        3. 返回检索结果，包含文档内容和相似度分数

        Args:
            query: 查询文本
            n_results: 返回结果数量，默认 5

        Returns:
            检索结果列表，每个结果包含 "content"、"metadata" 和 "score" 字段
        """
        if not query.strip():
            logger.warning("查询文本为空")
            return []

        # 将查询文本转换为向量
        logger.debug(f"开始对查询文本进行 Embedding: {query[:50]}...")
        query_embedding = self._embed([query])[0]

        # 在 Chroma 中检索相似向量
        # include 参数指定返回哪些字段：documents（文档内容）、metadatas（元数据）、distances（距离）
        logger.debug(f"开始检索相似文档，返回数量: {n_results}")
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

        # 处理检索结果
        # 将 Chroma 返回的格式转换为更友好的格式
        formatted_results = []
        for i in range(len(results["ids"][0])):
            # 计算相似度分数（Chroma 返回的是距离，需要转换为相似度）
            # 相似度 = 1 / (1 + 距离)，范围在 0-1 之间，值越大越相似
            distance = results["distances"][0][i]
            score = 1 / (1 + distance)

            # 构建结果字典
            formatted_results.append({
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "score": round(score, 4),  # 保留 4 位小数
            })

        # 记录检索完成日志
        logger.debug(f"检索完成，找到 {len(formatted_results)} 个相似文档")

        return formatted_results

    def get_document_count(self) -> int:
        """
        获取向量库中文档数量

        业务逻辑：
        返回 Chroma Collection 中的文档总数

        Returns:
            文档数量
        """
        count = self._collection.count()
        logger.debug(f"向量库文档数量: {count}")
        return count

    def clear(self):
        """
        清空向量库

        业务逻辑：
        删除 Chroma Collection 中的所有文档
        """
        logger.warning("开始清空向量库")
        self._collection.delete(ids=self._collection.get()["ids"])
        logger.warning("向量库已清空")

    def rebuild(self, documents: List[Dict[str, Any]]):
        """
        重建向量库

        业务逻辑：
        1. 清空现有向量库
        2. 添加新文档

        Args:
            documents: 新文档列表
        """
        logger.info("开始重建向量库...")
        self.clear()
        self.add_documents(documents)
        logger.info("向量库重建完成")


# 创建全局向量存储实例
vector_store = VectorStore()