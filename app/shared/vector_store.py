"""
向量存储服务模块

业务说明：
本模块负责封装 Chroma 向量数据库的操作，提供文档检索能力。
使用 BGE-small-zh-v1.5 作为 Embedding 模型，将文本转换为向量。
支持扩展元数据字段（source、quality_score、match_count、helpful_count 等）。

设计思路：
1. 使用 Chroma 作为本地向量数据库，支持持久化存储
2. 使用 sentence-transformers 加载 BGE-small-zh-v1.5 模型
3. 封装检索、添加、更新、删除等常用操作
4. 提供单例模式，确保全局只有一个向量存储实例
5. 支持扩展元数据字段，用于知识飞轮（质量评分、反馈统计）
"""

import logging
import os
import uuid
from datetime import datetime
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
    支持扩展元数据字段，用于知识飞轮和质量评分。
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
        初始化向量存储服务（轻量初始化，延迟加载模型和数据库）

        业务逻辑：
        1. 仅设置初始化标记和线程锁，不加载模型和数据库
        2. 实际初始化在第一次调用公共方法时通过 _ensure_initialized() 执行
        3. 延迟初始化的目的：避免 import 阶段加载模型，提升服务启动健壮性
        """
        # 防止重复初始化
        if hasattr(self, '_initialized'):
            return

        # 初始化标记（False 表示尚未初始化）
        self._initialized = False

        # 线程锁，确保并发安全的延迟初始化
        import threading
        self._init_lock = threading.Lock()

    def _ensure_initialized(self):
        """
        确保向量存储已初始化（延迟加载）

        业务逻辑：
        第一次调用时执行实际的初始化工作（加载模型、初始化 ChromaDB 等）。
        使用双重检查锁定确保并发安全。
        """
        # 第一次检查：无锁快速路径
        if self._initialized:
            return

        # 获取锁
        with self._init_lock:
            # 第二次检查：确保只有一个线程执行初始化
            if not self._initialized:
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
        1. 确保向量存储已初始化（延迟加载）
        2. 提取文档内容和元数据
        3. 将文档内容转换为向量
        4. 将向量和元数据写入 Chroma
        5. 支持扩展元数据字段（source、quality_score、match_count、helpful_count 等）

        Args:
            documents: 文档列表，每个文档包含 "content"、"metadata" 和可选的 "id" 字段
        """
        # 确保向量存储已初始化（延迟加载）
        self._ensure_initialized()

        if not documents:
            logger.warning("尝试添加空文档列表")
            return

        # 提取文档内容、ID 和元数据
        ids = []
        contents = []
        metadatas = []

        for i, doc in enumerate(documents):
            # 使用文档自带的 ID，或者生成新的唯一 ID
            doc_id = doc.get("id") or f"doc_{uuid.uuid4().hex[:8]}"
            ids.append(doc_id)
            # 获取文档内容
            contents.append(doc.get("content", ""))

            # 获取文档元数据，添加默认值
            metadata = doc.get("metadata", {})
            # 确保必需的扩展元数据字段存在，添加默认值
            metadata.setdefault("source", "admin")
            metadata.setdefault("quality_score", 0.8)
            metadata.setdefault("match_count", 0)
            metadata.setdefault("helpful_count", 0)
            metadata.setdefault("category", "未分类")
            metadata.setdefault("doc_id", doc_id)
            metadata.setdefault("file_name", "")
            metadata.setdefault("created_at", datetime.now().isoformat())
            metadata.setdefault("updated_at", datetime.now().isoformat())
            metadata.setdefault("chunk_index", 0)
            metadata.setdefault("total_chunks", 1)

            metadatas.append(metadata)

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
        1. 确保向量存储已初始化（延迟加载）
        2. 将查询文本转换为向量
        3. 在 Chroma 中检索相似向量
        4. 返回检索结果，包含文档内容和相似度分数
        5. 更新被匹配文档的 match_count

        Args:
            query: 查询文本
            n_results: 返回结果数量，默认 5

        Returns:
            检索结果列表，每个结果包含 "content"、"metadata" 和 "score" 字段
        """
        # 确保向量存储已初始化（延迟加载）
        self._ensure_initialized()

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
            include=["documents", "metadatas", "distances", "ids"],
        )

        # 处理检索结果
        # 将 Chroma 返回的格式转换为更友好的格式
        formatted_results = []
        matched_ids = []

        for i in range(len(results["ids"][0])):
            # 记录被匹配的文档 ID，用于后续更新 match_count
            matched_ids.append(results["ids"][0][i])

            # 计算相似度分数（Chroma 返回的是距离，需要转换为相似度）
            # 相似度 = 1 / (1 + 距离)，范围在 0-1 之间，值越大越相似
            distance = results["distances"][0][i]
            score = 1 / (1 + distance)

            # 构建结果字典
            formatted_results.append({
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "score": round(score, 4),  # 保留 4 位小数
                "id": results["ids"][0][i],
            })

        # 更新被匹配文档的 match_count
        self._update_match_count(matched_ids)

        # 记录检索完成日志
        logger.debug(f"检索完成，找到 {len(formatted_results)} 个相似文档")

        return formatted_results

    def _update_match_count(self, ids: List[str]):
        """
        更新文档的匹配计数

        业务逻辑：
        当文档被检索匹配时，增加其 match_count，用于知识飞轮质量评分

        Args:
            ids: 文档 ID 列表
        """
        if not ids:
            return

        try:
            # 获取这些文档的当前元数据
            existing_data = self._collection.get(ids=ids, include=["metadatas"])

            # 构建更新后的元数据
            new_metadatas = []
            for i, id_ in enumerate(ids):
                if i < len(existing_data["metadatas"]):
                    metadata = existing_data["metadatas"][i].copy()
                    metadata["match_count"] = metadata.get("match_count", 0) + 1
                    metadata["updated_at"] = datetime.now().isoformat()
                    new_metadatas.append(metadata)

            # 更新元数据
            if new_metadatas:
                self._collection.update(ids=ids, metadatas=new_metadatas)
                logger.debug(f"更新了 {len(ids)} 个文档的 match_count")
        except Exception as e:
            logger.error(f"更新 match_count 失败: {str(e)}")

    def update_quality_score(self, doc_id: str, feedback: int):
        """
        根据用户反馈更新知识质量分

        业务逻辑：
        - 确保向量存储已初始化（延迟加载）
        - 👍（feedback=1）：quality_score += 0.1，helpful_count += 1
        - 👎（feedback=-1）：quality_score -= 0.2
        - 同时更新 match_count 和 updated_at

        Args:
            doc_id: 文档 ID
            feedback: 反馈值，1=👍，-1=👎
        """
        # 确保向量存储已初始化（延迟加载）
        self._ensure_initialized()

        try:
            # 获取文档当前元数据
            existing_data = self._collection.get(ids=[doc_id], include=["metadatas"])

            if not existing_data["metadatas"]:
                logger.warning(f"文档 {doc_id} 不存在，无法更新质量分")
                return

            metadata = existing_data["metadatas"][0].copy()

            # 更新质量分
            current_score = metadata.get("quality_score", 0.8)
            if feedback == 1:
                metadata["quality_score"] = min(1.0, current_score + 0.1)
                metadata["helpful_count"] = metadata.get("helpful_count", 0) + 1
            elif feedback == -1:
                metadata["quality_score"] = max(0.0, current_score - 0.2)

            # 更新匹配计数和时间戳
            metadata["match_count"] = metadata.get("match_count", 0) + 1
            metadata["updated_at"] = datetime.now().isoformat()

            # 保存更新后的元数据
            self._collection.update(ids=[doc_id], metadatas=[metadata])

            logger.info(f"文档 {doc_id} 质量分已更新: {metadata['quality_score']}")
        except Exception as e:
            logger.error(f"更新质量分失败: {str(e)}")

    def get_document_count(self) -> int:
        """
        获取向量库中文档数量

        业务逻辑：
        1. 确保向量存储已初始化（延迟加载）
        2. 返回 Chroma Collection 中的文档总数

        Returns:
            文档数量
        """
        # 确保向量存储已初始化（延迟加载）
        self._ensure_initialized()

        count = self._collection.count()
        logger.debug(f"向量库文档数量: {count}")
        return count

    def clear(self):
        """
        清空向量库

        业务逻辑：
        1. 确保向量存储已初始化（延迟加载）
        2. 删除 Chroma Collection 中的所有文档
        """
        # 确保向量存储已初始化（延迟加载）
        self._ensure_initialized()

        logger.warning("开始清空向量库")
        self._collection.delete(ids=self._collection.get()["ids"])
        logger.warning("向量库已清空")

    def rebuild(self, documents: List[Dict[str, Any]]):
        """
        重建向量库

        业务逻辑：
        1. 确保向量存储已初始化（延迟加载）
        2. 清空现有向量库
        3. 添加新文档

        Args:
            documents: 新文档列表
        """
        # 确保向量存储已初始化（延迟加载）
        self._ensure_initialized()

        logger.info("开始重建向量库...")
        self.clear()
        self.add_documents(documents)
        logger.info("向量库重建完成")

    def get_documents_by_doc_id(self, doc_id: str) -> List[Dict[str, Any]]:
        """
        根据 doc_id 获取所有相关文档（同一原始文档的所有 chunks）

        业务逻辑：
        1. 确保向量存储已初始化（延迟加载）
        2. 使用 Chroma 的 where 子句查询所有具有相同 doc_id 的文档

        Args:
            doc_id: 原始文档 ID

        Returns:
            文档列表
        """
        # 确保向量存储已初始化（延迟加载）
        self._ensure_initialized()

        try:
            results = self._collection.get(
                where={"doc_id": doc_id},
                include=["documents", "metadatas", "ids"],
            )

            formatted_results = []
            for i in range(len(results["ids"])):
                formatted_results.append({
                    "id": results["ids"][i],
                    "content": results["documents"][i],
                    "metadata": results["metadatas"][i],
                })

            return formatted_results
        except Exception as e:
            logger.error(f"根据 doc_id 获取文档失败: {str(e)}")
            return []

    def delete_by_doc_id(self, doc_id: str):
        """
        根据 doc_id 删除所有相关文档（同一原始文档的所有 chunks）

        业务逻辑：
        1. 确保向量存储已初始化（延迟加载）
        2. 使用 Chroma 的 delete 方法，通过 where 子句删除所有具有相同 doc_id 的文档

        Args:
            doc_id: 原始文档 ID
        """
        # 确保向量存储已初始化（延迟加载）
        self._ensure_initialized()

        try:
            # 先获取所有相关文档的 ID
            results = self._collection.get(where={"doc_id": doc_id}, include=[])
            if results["ids"]:
                self._collection.delete(ids=results["ids"])
                logger.info(f"成功删除 doc_id={doc_id} 的 {len(results['ids'])} 个文档")
            else:
                logger.warning(f"未找到 doc_id={doc_id} 的文档")
        except Exception as e:
            logger.error(f"删除文档失败: {str(e)}")

    def get_all_documents(self, category: str = None) -> List[Dict[str, Any]]:
        """
        获取所有文档（支持按分类筛选）

        业务逻辑：
        1. 确保向量存储已初始化（延迟加载）
        2. 返回向量库中的所有文档，支持按 category 筛选

        Args:
            category: 分类名称，可选

        Returns:
            文档列表
        """
        # 确保向量存储已初始化（延迟加载）
        self._ensure_initialized()

        try:
            where = {"category": category} if category else None
            results = self._collection.get(
                where=where,
                include=["documents", "metadatas", "ids"],
            )

            formatted_results = []
            for i in range(len(results["ids"])):
                formatted_results.append({
                    "id": results["ids"][i],
                    "content": results["documents"][i],
                    "metadata": results["metadatas"][i],
                })

            return formatted_results
        except Exception as e:
            logger.error(f"获取所有文档失败: {str(e)}")
            return []

    def get_categories(self) -> List[Dict[str, Any]]:
        """
        获取所有知识分类及其文档数量

        业务逻辑：
        1. 确保向量存储已初始化（延迟加载）
        2. 查询向量库中所有不同的 category，并统计每个分类的文档数量

        Returns:
            分类列表，每个分类包含 name 和 count
        """
        # 确保向量存储已初始化（延迟加载）
        self._ensure_initialized()

        try:
            # 获取所有文档的元数据
            results = self._collection.get(include=["metadatas"])

            # 统计每个分类的文档数量
            category_counts = {}
            for metadata in results["metadatas"]:
                category = metadata.get("category", "未分类")
                category_counts[category] = category_counts.get(category, 0) + 1

            # 转换为列表格式
            categories = []
            for name, count in category_counts.items():
                categories.append({"name": name, "count": count})

            return categories
        except Exception as e:
            logger.error(f"获取分类列表失败: {str(e)}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """
        获取向量库统计信息

        业务逻辑：
        1. 确保向量存储已初始化（延迟加载）
        2. 返回文档总数、向量总数、分类数量等统计信息

        Returns:
            统计信息字典
        """
        # 确保向量存储已初始化（延迟加载）
        self._ensure_initialized()

        try:
            total_count = self.get_document_count()
            categories = self.get_categories()

            # 获取质量分分布
            results = self._collection.get(include=["metadatas"])
            quality_scores = []
            for metadata in results["metadatas"]:
                quality_scores.append(metadata.get("quality_score", 0.8))

            avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.8

            return {
                "total_documents": total_count,
                "total_categories": len(categories),
                "categories": categories,
                "avg_quality_score": round(avg_quality, 4),
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {str(e)}")
            return {}

    def cleanup_low_quality_knowledge(self, threshold: float = 0.3):
        """
        清理低质量用户知识

        业务逻辑：
        1. 确保向量存储已初始化（延迟加载）
        2. 删除 source=user 且 quality_score < threshold 的知识

        Args:
            threshold: 质量分阈值，默认 0.3
        """
        # 确保向量存储已初始化（延迟加载）
        self._ensure_initialized()

        try:
            # 查询所有 source=user 的文档
            results = self._collection.get(
                where={"source": "user"},
                include=["metadatas", "ids"],
            )

            # 筛选出质量分低于阈值的文档
            low_quality_ids = []
            for i, metadata in enumerate(results["metadatas"]):
                if metadata.get("quality_score", 0.8) < threshold:
                    low_quality_ids.append(results["ids"][i])

            # 删除低质量文档
            if low_quality_ids:
                self._collection.delete(ids=low_quality_ids)
                logger.info(f"清理了 {len(low_quality_ids)} 个低质量用户知识")
            else:
                logger.info("没有需要清理的低质量用户知识")
        except Exception as e:
            logger.error(f"清理低质量知识失败: {str(e)}")

    def ensure_metadata_completeness(self):
        """
        确保向量库中所有文档的元数据完整

        业务逻辑：
        1. 确保向量存储已初始化（延迟加载）
        2. 遍历所有文档，为缺失的扩展元数据字段添加默认值
        3. 用于服务启动时补全旧数据的元数据
        """
        # 确保向量存储已初始化（延迟加载）
        self._ensure_initialized()

        try:
            # 获取所有文档的 ID 和元数据
            results = self._collection.get(include=["metadatas", "ids"])

            # 检查并更新元数据
            updated_ids = []
            updated_metadatas = []

            for i, metadata in enumerate(results["metadatas"]):
                needs_update = False
                new_metadata = metadata.copy()

                # 检查并添加缺失的字段
                if "source" not in new_metadata:
                    new_metadata["source"] = "admin"
                    needs_update = True
                if "quality_score" not in new_metadata:
                    new_metadata["quality_score"] = 0.8
                    needs_update = True
                if "match_count" not in new_metadata:
                    new_metadata["match_count"] = 0
                    needs_update = True
                if "helpful_count" not in new_metadata:
                    new_metadata["helpful_count"] = 0
                    needs_update = True
                if "category" not in new_metadata:
                    new_metadata["category"] = "未分类"
                    needs_update = True
                if "doc_id" not in new_metadata:
                    new_metadata["doc_id"] = results["ids"][i]
                    needs_update = True
                if "file_name" not in new_metadata:
                    new_metadata["file_name"] = ""
                    needs_update = True
                if "created_at" not in new_metadata:
                    new_metadata["created_at"] = datetime.now().isoformat()
                    needs_update = True
                if "updated_at" not in new_metadata:
                    new_metadata["updated_at"] = datetime.now().isoformat()
                    needs_update = True
                if "chunk_index" not in new_metadata:
                    new_metadata["chunk_index"] = 0
                    needs_update = True
                if "total_chunks" not in new_metadata:
                    new_metadata["total_chunks"] = 1
                    needs_update = True

                if needs_update:
                    updated_ids.append(results["ids"][i])
                    updated_metadatas.append(new_metadata)

            # 批量更新元数据
            if updated_ids:
                self._collection.update(ids=updated_ids, metadatas=updated_metadatas)
                logger.info(f"补全了 {len(updated_ids)} 个文档的元数据")
            else:
                logger.info("所有文档的元数据已完整")
        except Exception as e:
            logger.error(f"补全元数据失败: {str(e)}")


# 创建全局向量存储实例
vector_store = VectorStore()
