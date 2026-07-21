"""
喂养事件向量存储模块

业务说明：
本模块负责管理喂养事件的向量存储，用于意图识别中的事件匹配和数据飞轮闭环。
使用独立的 ChromaDB Collection（feeding_events）存储事件向量，与母婴知识向量库隔离。
支持标准事件和用户表达两种数据来源，标准事件来自事件字典，用户表达来自用户实际输入。

设计思路：
1. 复用与知识向量库相同的 ChromaDB 客户端和 Embedding 模型（BAAI/bge-small-zh-v1.5）
2. 使用独立的 feeding_events Collection，避免与知识库数据混淆
3. 标准事件生成动作变体（开始/结束/记录 + 事件名），覆盖常见用户表达模式
4. 用户表达作为数据飞轮的输入，持续优化事件匹配准确率
5. 提供质量评估和清理机制，防止低质量样本污染向量库

使用场景：
- 意图识别：根据用户输入检索最相似的喂养事件
- 数据飞轮：记录用户实际表达，持续优化匹配效果
- 事件同步：当事件字典变更时，增量同步标准事件向量
- 质量治理：定期清理低质量用户表达，保持向量库健康
"""

import logging
import math
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from app.config.settings import settings

# 初始化日志记录器
logger = logging.getLogger(__name__)

# 标准事件的动作变体列表，用于生成不同动作的表达
STANDARD_ACTIONS = ["开始", "结束", "记录"]


class EventVectorStore:
    """
    喂养事件向量存储类

    业务说明：
    管理喂养事件的向量存储，支持标准事件和用户表达两种数据来源。
    标准事件来自事件字典，用户表达来自用户实际输入（数据飞轮）。
    """

    def __init__(self):
        """
        初始化喂养事件向量存储（轻量初始化，延迟加载模型和数据库）

        业务逻辑：
        1. 仅设置初始化标记和线程锁，不加载模型和数据库
        2. 实际初始化在第一次调用公共方法时通过 _ensure_initialized() 执行
        3. 延迟初始化的目的：避免 import 阶段加载模型，提升服务启动健壮性

        Args:
            无

        Returns:
            无

        Side Effects:
            无
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
        确保喂养事件向量存储已初始化（延迟加载）

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
                logger.info("开始初始化喂养事件向量存储...")

                # 创建数据目录（如果不存在），确保 ChromaDB 持久化目录存在
                os.makedirs(settings.chroma_persist_dir, exist_ok=True)

                # 加载 Embedding 模型
                # 复用与知识向量库相同的 BAAI/bge-small-zh-v1.5 模型，保证向量空间一致
                logger.info(f"加载 Embedding 模型: {settings.embedding_model}")
                self._embedding_model = SentenceTransformer(
                    settings.embedding_model,  # 使用配置中的模型名称
                    cache_folder=os.path.join("data", "models"),  # 模型缓存目录
                )

                # 初始化 ChromaDB 客户端
                # 复用与知识向量库相同的客户端配置，数据存储在同一持久化目录下
                logger.info(f"初始化 ChromaDB 客户端，数据目录: {settings.chroma_persist_dir}")
                self._chroma_client = chromadb.PersistentClient(
                    path=settings.chroma_persist_dir,  # 持久化存储路径
                    settings=Settings(
                        anonymized_telemetry=False,  # 禁用匿名遥测，保护隐私
                        allow_reset=False,  # 禁止重置，防止误操作清空数据
                    ),
                )

                # 创建或获取 feeding_events Collection
                # 使用独立 Collection 存储喂养事件，与母婴知识库隔离
                self._collection = self._chroma_client.get_or_create_collection(
                    name="feeding_events",  # Collection 名称，与知识库区分
                    metadata={"description": "喂养事件向量库"},  # 描述信息
                )

                # 标记初始化完成
                self._initialized = True

                # 记录初始化完成日志
                logger.info("喂养事件向量存储初始化完成")

    def _embed(self, texts: List[str]) -> List[List[float]]:
        """
        将文本列表转换为向量列表

        业务逻辑：
        使用 BGE-small-zh-v1.5 模型将文本编码为向量

        Args:
            texts: 待编码的文本列表

        Returns:
            向量列表，每个向量是一个浮点数列表

        Side Effects:
            无
        """
        # 使用 Embedding 模型对文本列表进行编码
        embeddings = self._embedding_model.encode(texts)
        # 将 numpy 数组转换为 Python 列表，适配 ChromaDB 接口
        return embeddings.tolist()

    def search_events(self, query: str, n_results: int = 3) -> List[Dict]:
        """
        在喂养事件向量库中搜索相似事件

        业务逻辑：
        1. 确保向量存储已初始化（延迟加载）
        2. 将查询文本转换为向量
        3. 在 feeding_events Collection 中检索最相似的事件
        4. 将距离转换为相似度分数并格式化返回结果

        Args:
            query: 用户输入的查询文本
            n_results: 返回结果数量，默认为 3

        Returns:
            检索结果列表，每个结果包含 id、score 和 metadata 字段

        Side Effects:
            无
        """
        # 确保向量存储已初始化（延迟加载）
        self._ensure_initialized()

        # 检查查询文本是否为空，空查询无法进行语义匹配
        if not query.strip():
            logger.warning("查询文本为空，无法搜索事件")
            return []

        # 将查询文本转换为向量
        logger.debug(f"开始对查询文本进行 Embedding: {query[:50]}...")
        query_embedding = self._embed([query])[0]

        # 在 ChromaDB 中检索相似向量
        logger.debug(f"开始检索相似事件，返回数量: {n_results}")
        results = self._collection.query(
            query_embeddings=[query_embedding],  # 查询向量
            n_results=n_results,  # 返回结果数量
            include=["documents", "metadatas", "distances"],  # 包含文档内容、元数据和距离
        )

        # 处理检索结果，将 ChromaDB 返回格式转换为业务友好的格式
        formatted_results = []
        for i in range(len(results["ids"][0])):
            # 计算相似度分数：将距离转换为 0-1 之间的相似度值
            # 相似度 = 1 / (1 + 距离)，距离越小相似度越高
            distance = results["distances"][0][i]
            score = 1 / (1 + distance)

            # 构建单条结果字典，包含 id、分数和元数据
            formatted_results.append({
                "id": results["ids"][0][i],  # 向量记录 ID
                "score": round(score, 4),  # 相似度分数，保留 4 位小数
                "metadata": results["metadatas"][0][i],  # 元数据信息
            })

        # 记录检索完成日志
        logger.debug(f"事件检索完成，找到 {len(formatted_results)} 个相似事件")

        return formatted_results

    def add_user_expression(self, event_id: str, event_name: str, expression: str, action: Optional[str] = None) -> str:
        """
        添加用户表达到向量库（数据飞轮）

        业务逻辑：
        1. 确保向量存储已初始化（延迟加载）
        2. 为用户表达生成唯一 ID
        3. 构建元数据，记录事件关联信息和统计数据
        4. 将用户表达文本转换为向量并存入 Collection

        Args:
            event_id: 关联的事件 ID
            event_name: 关联的事件名称
            expression: 用户的自然语言表达
            action: 动作类型（开始/结束/记录），可选

        Returns:
            生成的向量记录 ID

        Side Effects:
            - 向 feeding_events Collection 添加一条新记录
            - 新记录的 match_count 和 success_count 初始为 0
        """
        # 确保向量存储已初始化（延迟加载）
        self._ensure_initialized()

        # 生成唯一的向量记录 ID，使用 uuid4 确保全局唯一
        vector_id = f"user_{uuid.uuid4().hex}"

        # 获取当前时间作为创建时间，格式为 ISO 8601
        created_at = datetime.now().isoformat()

        # 构建元数据字典，包含事件关联信息和统计数据
        metadata = {
            "event_id": event_id,  # 关联的事件 ID
            "event_name": event_name,  # 关联的事件名称
            "source": "user",  # 数据来源标记为用户表达
            "action": action or "",  # 动作类型，未指定则为空字符串
            "match_count": 0,  # 匹配次数，初始为 0
            "success_count": 0,  # 成功次数，初始为 0
            "created_at": created_at,  # 创建时间
        }

        # 将用户表达文本转换为向量
        embedding = self._embed([expression])[0]

        # 将用户表达添加到 feeding_events Collection
        self._collection.add(
            ids=[vector_id],  # 唯一 ID
            embeddings=[embedding],  # 向量
            documents=[expression],  # 原始文本
            metadatas=[metadata],  # 元数据
        )

        # 记录添加成功日志
        logger.info(f"添加用户表达到向量库: event_id={event_id}, expression={expression[:30]}..., vector_id={vector_id}")

        return vector_id

    def increment_match_count(self, vector_id: str):
        """
        递增向量记录的匹配次数

        业务逻辑：
        1. 确保向量存储已初始化（延迟加载）
        2. 根据 vector_id 获取当前记录的元数据
        3. 将 match_count 加 1
        4. 更新记录的元数据

        Args:
            vector_id: 向量记录 ID

        Returns:
            无

        Side Effects:
            - 修改指定记录的 match_count 元数据值
        """
        # 确保向量存储已初始化（延迟加载）
        self._ensure_initialized()

        # 根据 ID 获取记录的元数据
        result = self._collection.get(
            ids=[vector_id],  # 目标记录 ID
            include=["metadatas"],  # 只获取元数据
        )

        # 检查记录是否存在
        if not result["metadatas"]:
            logger.warning(f"未找到向量记录: {vector_id}")
            return

        # 获取当前元数据
        metadata = result["metadatas"][0]
        # 将匹配次数加 1
        current_count = metadata.get("match_count", 0)
        metadata["match_count"] = current_count + 1

        # 更新记录的元数据
        self._collection.update(
            ids=[vector_id],  # 目标记录 ID
            metadatas=[metadata],  # 更新后的元数据
        )

        # 记录更新日志
        logger.debug(f"递增匹配次数: vector_id={vector_id}, match_count={metadata['match_count']}")

    def increment_success_count(self, vector_id: str):
        """
        递增向量记录的成功次数

        业务逻辑：
        1. 确保向量存储已初始化（延迟加载）
        2. 根据 vector_id 获取当前记录的元数据
        3. 将 success_count 加 1
        4. 更新记录的元数据

        Args:
            vector_id: 向量记录 ID

        Returns:
            无

        Side Effects:
            - 修改指定记录的 success_count 元数据值
        """
        # 确保向量存储已初始化（延迟加载）
        self._ensure_initialized()

        # 根据 ID 获取记录的元数据
        result = self._collection.get(
            ids=[vector_id],  # 目标记录 ID
            include=["metadatas"],  # 只获取元数据
        )

        # 检查记录是否存在
        if not result["metadatas"]:
            logger.warning(f"未找到向量记录: {vector_id}")
            return

        # 获取当前元数据
        metadata = result["metadatas"][0]
        # 将成功次数加 1
        current_count = metadata.get("success_count", 0)
        metadata["success_count"] = current_count + 1

        # 更新记录的元数据
        self._collection.update(
            ids=[vector_id],  # 目标记录 ID
            metadatas=[metadata],  # 更新后的元数据
        )

        # 记录更新日志
        logger.debug(f"递增成功次数: vector_id={vector_id}, success_count={metadata['success_count']}")

    def delete_vector(self, vector_id: str):
        """
        删除向量记录

        业务逻辑：
        1. 确保向量存储已初始化（延迟加载）
        2. 检查记录是否存在
        3. 验证记录来源是否为用户表达（source="user"）
        4. 仅允许删除用户表达记录，标准记录禁止删除
        5. 执行删除操作

        Args:
            vector_id: 向量记录 ID

        Returns:
            无

        Side Effects:
            - 从 feeding_events Collection 中永久删除指定记录
        """
        # 确保向量存储已初始化（延迟加载）
        self._ensure_initialized()

        # 根据 ID 获取记录的元数据，用于验证来源
        result = self._collection.get(
            ids=[vector_id],  # 目标记录 ID
            include=["metadatas"],  # 只获取元数据
        )

        # 检查记录是否存在
        if not result["metadatas"]:
            logger.warning(f"未找到向量记录: {vector_id}")
            return

        # 获取记录元数据
        metadata = result["metadatas"][0]
        # 获取数据来源
        source = metadata.get("source", "")

        # 安全检查：仅允许删除用户表达记录，禁止删除标准记录
        # 标准记录是事件字典同步的基础数据，不能随意删除
        if source != "user":
            logger.warning(f"禁止删除标准记录: vector_id={vector_id}, source={source}")
            return

        # 执行删除操作
        self._collection.delete(ids=[vector_id])

        # 记录删除成功日志
        logger.info(f"删除用户表达记录: vector_id={vector_id}")

    def sync_events(self, event_dictionary: List[Dict], added_events: List[Dict], removed_event_ids: List[str], modified_events: List[Dict]):
        """
        同步事件字典变更到向量库

        业务逻辑：
        1. 确保向量存储已初始化（延迟加载）
        2. 处理新增事件：为每个新事件生成标准条目和动作变体条目
        3. 处理删除事件：删除标准条目及关联的用户表达
        4. 处理修改事件：更新标准条目的内容和元数据

        Args:
            event_dictionary: 完整的事件字典列表
            added_events: 新增的事件列表
            removed_event_ids: 删除的事件 ID 列表
            modified_events: 修改的事件列表

        Returns:
            无

        Side Effects:
            - 向 feeding_events Collection 添加/删除/更新记录
            - 删除事件时同时删除关联的用户表达记录
        """
        # 确保向量存储已初始化（延迟加载）
        self._ensure_initialized()

        # 处理新增事件
        for event in added_events:
            # 获取事件 ID 和名称
            event_id = event.get("id", "")
            event_name = event.get("name", "")

            # 为事件生成标准条目，包含动作变体
            self._add_standard_event(event_id=event_id, event_name=event_name)

            # 记录新增事件日志
            logger.info(f"同步新增事件: event_id={event_id}, event_name={event_name}")

        # 处理删除事件
        for event_id in removed_event_ids:
            # 删除标准条目及关联的用户表达
            self._remove_event_by_id(event_id)

            # 记录删除事件日志
            logger.info(f"同步删除事件: event_id={event_id}")

        # 处理修改事件
        for event in modified_events:
            # 获取事件 ID 和名称
            event_id = event.get("id", "")
            event_name = event.get("name", "")

            # 先删除旧的标准条目
            self._remove_standard_entries_by_event_id(event_id)

            # 再添加新的标准条目
            self._add_standard_event(event_id=event_id, event_name=event_name)

            # 记录修改事件日志
            logger.info(f"同步修改事件: event_id={event_id}, event_name={event_name}")

    def _add_standard_event(self, event_id: str, event_name: str):
        """
        为事件添加标准条目（含动作变体）

        业务逻辑：
        1. 添加事件名称本身作为基础标准条目
        2. 为每个动作（开始/结束/记录）生成变体条目

        Args:
            event_id: 事件 ID
            event_name: 事件名称

        Returns:
            无

        Side Effects:
            - 向 feeding_events Collection 添加多条标准记录
        """
        # 存储待添加的批量数据
        ids = []
        documents = []
        metadatas = []
        embeddings_list = []

        # 添加事件名称本身作为基础标准条目
        base_id = f"std_{event_id}_base"  # 基础标准条目 ID
        ids.append(base_id)
        documents.append(event_name)
        metadatas.append({
            "event_id": event_id,  # 关联事件 ID
            "event_name": event_name,  # 事件名称
            "parent_id": "",  # 基础条目无父级
            "source": "standard",  # 来源标记为标准事件
            "action": "",  # 基础条目无动作
            "match_count": 0,  # 匹配次数初始为 0
            "success_count": 0,  # 成功次数初始为 0
            "created_at": datetime.now().isoformat(),  # 创建时间
        })

        # 为每个动作生成变体条目，覆盖常见的用户表达模式
        for action in STANDARD_ACTIONS:
            # 生成变体文本，格式为 "{动作}{事件名称}"，如 "开始喂奶"
            variant_text = f"{action}{event_name}"
            # 生成变体条目 ID
            variant_id = f"std_{event_id}_{action}"
            ids.append(variant_id)
            documents.append(variant_text)
            metadatas.append({
                "event_id": event_id,  # 关联事件 ID
                "event_name": event_name,  # 事件名称
                "parent_id": base_id,  # 父级为基础条目 ID
                "source": "standard",  # 来源标记为标准事件
                "action": action,  # 动作类型
                "match_count": 0,  # 匹配次数初始为 0
                "success_count": 0,  # 成功次数初始为 0
                "created_at": datetime.now().isoformat(),  # 创建时间
            })

        # 批量将所有文档转换为向量
        embeddings_list = self._embed(documents)

        # 批量写入 ChromaDB
        self._collection.upsert(
            ids=ids,  # ID 列表
            embeddings=embeddings_list,  # 向量列表
            documents=documents,  # 原始文本列表
            metadatas=metadatas,  # 元数据列表
        )

        # 记录添加成功日志
        logger.debug(f"添加标准事件条目: event_id={event_id}, event_name={event_name}, 条目数={len(ids)}")

    def _remove_event_by_id(self, event_id: str):
        """
        根据 event_id 删除事件的所有记录（标准条目 + 用户表达）

        业务逻辑：
        1. 查询所有匹配该 event_id 的记录
        2. 删除所有匹配的记录，包括标准条目和用户表达

        Args:
            event_id: 事件 ID

        Returns:
            无

        Side Effects:
            - 从 feeding_events Collection 中删除所有关联记录
        """
        # 根据元数据中的 event_id 过滤查询所有关联记录
        results = self._collection.get(
            where={"event_id": event_id},  # 按 event_id 过滤
            include=["metadatas"],  # 只获取元数据
        )

        # 如果存在关联记录，执行删除
        if results["ids"]:
            # 批量删除所有关联记录
            self._collection.delete(ids=results["ids"])
            # 记录删除日志
            logger.info(f"删除事件 {event_id} 的所有记录，共 {len(results['ids'])} 条")

    def _remove_standard_entries_by_event_id(self, event_id: str):
        """
        根据 event_id 仅删除标准条目（不删除用户表达）

        业务逻辑：
        1. 查询所有匹配该 event_id 且 source 为 standard 的记录
        2. 删除这些标准条目

        Args:
            event_id: 事件 ID

        Returns:
            无

        Side Effects:
            - 从 feeding_events Collection 中删除标准条目记录
        """
        # 根据元数据中的 event_id 和 source 过滤查询标准条目
        results = self._collection.get(
            where={
                "$and": [  # 同时满足两个条件
                    {"event_id": event_id},  # 匹配 event_id
                    {"source": "standard"},  # 来源为标准事件
                ]
            },
            include=["metadatas"],  # 只获取元数据
        )

        # 如果存在标准条目，执行删除
        if results["ids"]:
            # 批量删除标准条目
            self._collection.delete(ids=results["ids"])
            # 记录删除日志
            logger.debug(f"删除事件 {event_id} 的标准条目，共 {len(results['ids'])} 条")

    def initialize_events(self, event_dictionary: List[Dict]):
        """
        从事件字典初始化喂养事件向量库

        业务逻辑：
        1. 确保向量存储已初始化（延迟加载）
        2. 清除所有现有的标准数据（保留用户表达数据）
        3. 遍历事件字典，为每个事件生成标准条目和动作变体
        4. 批量写入向量库

        Args:
            event_dictionary: 事件字典列表，每个元素包含 id 和 name 字段

        Returns:
            无

        Side Effects:
            - 清除所有 source="standard" 的记录
            - 向 feeding_events Collection 添加所有事件的标准条目和动作变体
        """
        # 确保向量存储已初始化（延迟加载）
        self._ensure_initialized()

        # 记录初始化开始日志
        logger.info(f"开始初始化喂养事件向量库，事件数量: {len(event_dictionary)}")

        # 获取所有标准记录
        standard_results = self._collection.get(
            where={"source": "standard"},  # 只查询标准记录
            include=["metadatas"],  # 只获取元数据
        )

        # 删除所有现有的标准数据，保留用户表达数据
        if standard_results["ids"]:
            # 批量删除标准记录
            self._collection.delete(ids=standard_results["ids"])
            # 记录清除日志
            logger.info(f"清除现有标准数据，共 {len(standard_results['ids'])} 条")

        # 遍历事件字典，为每个事件添加标准条目和动作变体
        for event in event_dictionary:
            # 获取事件 ID 和名称
            event_id = event.get("id", "")
            event_name = event.get("name", "")

            # 跳过缺少关键字段的事件
            if not event_id or not event_name:
                logger.warning(f"跳过无效事件: event={event}")
                continue

            # 为事件生成标准条目和动作变体
            self._add_standard_event(event_id=event_id, event_name=event_name)

        # 记录初始化完成日志
        logger.info(f"喂养事件向量库初始化完成，共处理 {len(event_dictionary)} 个事件")

    def check_and_cleanup(self, max_records: int = 10000, cleanup_ratio: float = 0.2):
        """
        检查向量库记录数量并清理低质量用户表达

        业务逻辑：
        1. 确保向量存储已初始化（延迟加载）
        2. 检查记录总数是否超过阈值
        3. 获取所有用户表达记录
        4. 计算每条记录的质量分数（质量分 = 准确率 × 置信度）
        5. 按质量分数排序，删除最低的 cleanup_ratio 比例记录

        Args:
            max_records: 最大记录数阈值，默认 10000
            cleanup_ratio: 清理比例，默认 0.2（删除最低质量的 20%）

        Returns:
            无

        Side Effects:
            - 从 feeding_events Collection 中删除低质量的用户表达记录
        """
        # 确保向量存储已初始化（延迟加载）
        self._ensure_initialized()

        # 获取当前记录总数
        total_count = self._collection.count()

        # 检查是否超过最大记录阈值
        if total_count <= max_records:
            # 未超过阈值，无需清理
            logger.debug(f"记录总数 {total_count} 未超过阈值 {max_records}，无需清理")
            return

        # 记录清理开始日志
        logger.info(f"记录总数 {total_count} 超过阈值 {max_records}，开始清理低质量用户表达...")

        # 获取所有用户表达记录
        user_results = self._collection.get(
            where={"source": "user"},  # 只查询用户表达记录
            include=["metadatas"],  # 获取元数据用于质量评估
        )

        # 如果没有用户表达记录，无需清理
        if not user_results["ids"]:
            logger.info("没有用户表达记录，无需清理")
            return

        # 计算每条用户表达记录的质量分数
        # 质量分 = 准确率 × 置信度
        # 准确率 = success_count / match_count（匹配成功比例）
        # 置信度 = match_count 归一化值（匹配次数越多越可信）
        scored_records = []
        for i, record_id in enumerate(user_results["ids"]):
            # 获取元数据
            metadata = user_results["metadatas"][i]
            # 获取匹配次数和成功次数
            match_count = metadata.get("match_count", 0)
            success_count = metadata.get("success_count", 0)

            # 计算准确率：成功次数 / 匹配次数，避免除零错误
            accuracy = success_count / match_count if match_count > 0 else 0.0

            # 计算置信度：使用 match_count 的对数作为置信度
            # 匹配次数越多，置信度越高，但增长递减
            confidence = math.log1p(match_count)  # log1p(x) = ln(1+x)，避免 log(0)

            # 计算质量分数 = 准确率 × 置信度
            quality_score = accuracy * confidence

            # 将记录 ID 和质量分数加入列表
            scored_records.append({
                "id": record_id,  # 记录 ID
                "quality_score": quality_score,  # 质量分数
            })

        # 按质量分数升序排序，分数低的排在前面
        scored_records.sort(key=lambda x: x["quality_score"])

        # 计算需要清理的记录数量
        cleanup_count = max(1, int(len(scored_records) * cleanup_ratio))

        # 取质量分数最低的记录 ID 列表
        cleanup_ids = [record["id"] for record in scored_records[:cleanup_count]]

        # 批量删除低质量记录
        if cleanup_ids:
            # 执行删除操作
            self._collection.delete(ids=cleanup_ids)
            # 记录清理完成日志
            logger.info(f"清理低质量用户表达完成，删除 {len(cleanup_ids)} 条记录")

    def get_event_count(self) -> int:
        """
        获取喂养事件向量库中的记录总数

        业务逻辑：
        1. 确保向量存储已初始化（延迟加载）
        2. 返回 feeding_events Collection 中的记录总数

        Args:
            无

        Returns:
            记录总数

        Side Effects:
            无
        """
        # 确保向量存储已初始化（延迟加载）
        self._ensure_initialized()

        # 获取 Collection 中的记录总数
        count = self._collection.count()
        # 记录日志
        logger.debug(f"喂养事件向量库记录总数: {count}")
        return count


# 创建全局事件向量存储实例
event_vector_store = EventVectorStore()
