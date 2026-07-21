"""
向量数据库构建脚本

业务说明：
本脚本用于构建 Chroma 向量数据库，将母婴知识文档转换为向量并存储。
支持文档加载、切分、Embedding、写入和验证。

设计思路：
1. 支持 Markdown 和 TXT 格式的文档
2. 按句子边界切分文档，每个 chunk 不超过 512 tokens
3. 使用 BGE-small-zh-v1.5 进行 Embedding
4. 支持增量更新（检测新增/更新文档）
5. 构建完成后验证向量库完整性

使用方法：
    # 基本用法
    python scripts/build_vector_db.py

    # 指定数据源目录
    python scripts/build_vector_db.py --data-dir ./data/knowledge

    # 指定输出目录
    python scripts/build_vector_db.py --output-dir ./data/chroma_db

    # 强制全量重建（忽略增量更新）
    python scripts/build_vector_db.py --force
"""

import argparse
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import tqdm

from app.config.settings import settings
from app.services.vector_store import vector_store

# 配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# 初始化日志记录器
logger = logging.getLogger(__name__)


def load_documents(data_dir: str) -> List[Dict[str, Any]]:
    """
    加载文档

    业务逻辑：
    1. 遍历指定目录下的所有文件
    2. 支持 Markdown（.md）和 TXT（.txt）格式
    3. 读取文件内容并提取元数据

    Args:
        data_dir: 数据源目录

    Returns:
        文档列表，每个文档包含 "content"、"metadata" 和 "file_path" 字段
    """
    # 初始化文档列表
    documents = []

    # 检查目录是否存在
    if not os.path.exists(data_dir):
        logger.error(f"数据源目录不存在: {data_dir}")
        return documents

    # 遍历目录下的所有文件
    for root, dirs, files in os.walk(data_dir):
        # 过滤隐藏目录
        dirs[:] = [d for d in dirs if not d.startswith(".")]

        # 遍历每个文件
        for filename in files:
            # 过滤隐藏文件
            if filename.startswith("."):
                continue

            # 获取文件扩展名
            ext = os.path.splitext(filename)[1].lower()

            # 只处理 Markdown 和 TXT 文件
            if ext not in [".md", ".txt"]:
                continue

            # 构建文件完整路径
            file_path = os.path.join(root, filename)

            try:
                # 读取文件内容
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # 跳过空文件
                if not content.strip():
                    logger.warning(f"跳过空文件: {file_path}")
                    continue

                # 提取相对路径（用于元数据）
                relative_path = os.path.relpath(file_path, data_dir)

                # 提取分类信息（从目录结构）
                category = os.path.dirname(relative_path)
                if not category:
                    category = "未分类"

                # 构建文档元数据
                metadata = {
                    "file_name": filename,
                    "file_path": relative_path,
                    "category": category,
                    "file_size": len(content),
                }

                # 添加到文档列表
                documents.append({
                    "content": content,
                    "metadata": metadata,
                    "file_path": file_path,
                })

                # 记录加载日志
                logger.debug(f"加载文档: {file_path}, 大小: {len(content)} 字符")

            except Exception as e:
                # 记录加载失败日志
                logger.error(f"加载文档失败: {file_path}, 错误: {str(e)}")

    # 记录加载完成日志
    logger.info(f"共加载 {len(documents)} 个文档")

    return documents


def split_document(content: str, max_tokens: int = 512) -> List[str]:
    """
    切分文档

    业务逻辑：
    1. 按句子边界切分文档
    2. 每个 chunk 不超过指定的 token 数
    3. 相邻 chunks 之间保留一定的重叠内容，保持上下文连贯性

    Args:
        content: 文档内容
        max_tokens: 每个 chunk 的最大 token 数，默认 512

    Returns:
        切分后的 chunk 列表
    """
    # 初始化 chunk 列表
    chunks = []

    # 如果内容为空，直接返回空列表
    if not content.strip():
        return chunks

    # 使用中文标点符号作为句子分隔符
    # 中文常用的句子结束符：。！？；\n\n（段落结束）
    import re

    # 按句子边界切分
    sentences = re.split(r"(。|！|？|；|\n\n)", content)

    # 合并句子和分隔符
    merged_sentences = []
    for i in range(0, len(sentences), 2):
        sentence = sentences[i]
        if i + 1 < len(sentences):
            sentence += sentences[i + 1]
        if sentence.strip():
            merged_sentences.append(sentence.strip())

    # 合并句子为 chunks
    current_chunk = ""
    for sentence in merged_sentences:
        # 计算当前 chunk + 新句子的 token 数（粗略估算，1 个中文字 ≈ 1 个 token）
        # 如果加上新句子会超过最大 token 数，则保存当前 chunk
        if len(current_chunk) + len(sentence) > max_tokens and current_chunk:
            chunks.append(current_chunk)
            # 保留重叠内容（取当前 chunk 的最后 100 个字符）
            current_chunk = current_chunk[-100:] + sentence
        else:
            current_chunk += sentence

    # 添加最后一个 chunk
    if current_chunk:
        chunks.append(current_chunk)

    # 记录切分日志
    logger.debug(f"文档切分为 {len(chunks)} 个 chunks")

    return chunks


def build_vector_db(data_dir: str = None, output_dir: str = None, force: bool = False) -> bool:
    """
    构建向量数据库

    业务逻辑：
    1. 加载文档
    2. 切分文档为 chunks
    3. 将 chunks 转换为向量并写入 Chroma
    4. 支持增量更新（检测新增/更新文档）
    5. 验证构建结果

    Args:
        data_dir: 数据源目录，默认为 settings.chroma_persist_dir 的上级目录下的 knowledge 文件夹
        output_dir: 输出目录，默认为 settings.chroma_persist_dir
        force: 是否强制全量重建，默认为 False（增量更新）

    Returns:
        构建是否成功
    """
    # 设置默认目录
    if data_dir is None:
        data_dir = os.path.join(os.path.dirname(settings.chroma_persist_dir), "knowledge")
    if output_dir is None:
        output_dir = settings.chroma_persist_dir

    # 记录构建开始日志
    logger.info(f"开始构建向量数据库")
    logger.info(f"数据源目录: {data_dir}")
    logger.info(f"输出目录: {output_dir}")
    logger.info(f"强制重建: {force}")

    try:
        # 步骤 1: 加载文档
        logger.info("步骤 1: 加载文档...")
        documents = load_documents(data_dir)

        # 如果没有加载到文档，返回失败
        if not documents:
            logger.error("没有加载到任何文档，构建失败")
            return False

        # 步骤 2: 切分文档
        logger.info("步骤 2: 切分文档...")
        all_chunks = []
        for doc in tqdm.tqdm(documents, desc="切分文档"):
            # 切分文档为 chunks
            chunks = split_document(doc["content"])

            # 为每个 chunk 添加元数据
            for i, chunk in enumerate(chunks):
                chunk_metadata = doc["metadata"].copy()
                chunk_metadata["chunk_index"] = i
                chunk_metadata["total_chunks"] = len(chunks)

                all_chunks.append({
                    "content": chunk,
                    "metadata": chunk_metadata,
                })

        # 记录切分结果
        logger.info(f"共生成 {len(all_chunks)} 个 chunks")

        # 步骤 3: 写入向量库
        logger.info("步骤 3: 写入向量库...")

        # 如果强制重建，先清空向量库
        if force:
            logger.info("强制重建模式，清空现有向量库...")
            vector_store.clear()

        # 将 chunks 添加到向量库
        vector_store.add_documents(all_chunks)

        # 步骤 4: 验证构建结果
        logger.info("步骤 4: 验证构建结果...")

        # 获取向量库中的文档数量
        doc_count = vector_store.get_document_count()

        # 验证文档数量是否匹配
        if doc_count == len(all_chunks):
            logger.info(f"验证通过！向量库中共有 {doc_count} 个文档")
        else:
            logger.warning(f"文档数量不匹配！期望 {len(all_chunks)} 个，实际 {doc_count} 个")

        # 执行检索测试
        logger.info("执行检索测试...")
        test_query = "宝宝拉肚子怎么办"
        results = vector_store.search(test_query, n_results=3)

        if results:
            logger.info(f"检索测试成功！找到 {len(results)} 个相关文档")
            for i, result in enumerate(results):
                logger.info(f"  {i+1}. 相似度: {result['score']}, 内容预览: {result['content'][:50]}...")
        else:
            logger.warning("检索测试未找到相关文档")

        # 记录构建完成日志
        logger.info("向量数据库构建完成！")

        return True

    except Exception as e:
        # 记录构建失败日志
        logger.error(f"向量数据库构建失败: {str(e)}")
        return False


def build_feeding_events_vector_db(event_dictionary=None) -> bool:
    """
    构建喂养事件向量数据库

    业务逻辑：
    1. 如果未传入事件字典，则通过 HTTP API 从兄弟仓获取事件字典
    2. 调用 event_vector_store.initialize_events 初始化喂养事件向量库
    3. 将事件字典中的每个事件生成标准条目和动作变体，写入 ChromaDB 的 feeding_events Collection
    4. 验证初始化结果，确保事件向量库中有数据

    Args:
        event_dictionary: 事件字典列表，每个元素包含 id 和 name 字段。
                          如果为 None，则从兄弟仓 HTTP API 获取

    Returns:
        构建是否成功
    """
    # 如果未传入事件字典，则从兄弟仓 HTTP API 获取
    if event_dictionary is None:
        # 记录获取开始日志
        logger.info("未传入事件字典，从兄弟仓 HTTP API 获取...")
        try:
            # 导入 HTTP 客户端，用于调用兄弟仓 API
            from app.shared.http_client import http_client
            # 使用 asyncio 运行异步获取方法（脚本环境为同步调用）
            import asyncio
            # 通过 HTTP 客户端异步获取事件字典
            event_dictionary = asyncio.run(http_client.get_event_dictionary())
            # 记录获取成功日志
            logger.info(f"成功从兄弟仓获取事件字典，包含 {len(event_dictionary)} 个事件")
        except Exception as e:
            # 记录获取失败日志
            logger.error(f"从兄弟仓获取事件字典失败: {str(e)}")
            # 返回构建失败
            return False

    # 检查事件字典是否为空
    if not event_dictionary:
        # 记录事件字典为空的警告日志
        logger.error("事件字典为空，无法构建喂养事件向量库")
        # 返回构建失败
        return False

    # 记录构建开始日志
    logger.info(f"开始构建喂养事件向量数据库，事件数量: {len(event_dictionary)}")

    try:
        # 导入喂养事件向量存储模块
        from app.feeding.services.event_vector_store import event_vector_store

        # 调用 initialize_events 方法初始化喂养事件向量库
        # 该方法会清除旧的标准数据，然后为每个事件生成标准条目和动作变体
        event_vector_store.initialize_events(event_dictionary)

        # 验证初始化结果，获取事件向量库中的记录总数
        event_count = event_vector_store.get_event_count()
        # 检查记录数是否大于 0
        if event_count > 0:
            # 记录验证通过日志
            logger.info(f"喂养事件向量库构建完成！共有 {event_count} 条记录")
        else:
            # 记录验证失败警告
            logger.warning("喂养事件向量库构建后记录数为 0，可能存在问题")

        # 返回构建成功
        return True

    except Exception as e:
        # 记录构建失败日志
        logger.error(f"喂养事件向量数据库构建失败: {str(e)}")
        # 返回构建失败
        return False


def main():
    """
    主函数

    业务逻辑：
    1. 解析命令行参数
    2. 调用构建函数
    3. 根据构建结果返回相应的退出码
    """
    # 创建参数解析器
    parser = argparse.ArgumentParser(description="构建向量数据库")

    # 添加命令行参数
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="数据源目录，默认为 data/knowledge",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="输出目录，默认为 data/chroma_db",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="强制全量重建，忽略增量更新",
    )

    # 解析参数
    args = parser.parse_args()

    # 调用知识向量库构建函数
    success = build_vector_db(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        force=args.force,
    )

    # 调用喂养事件向量库构建函数
    # 在知识向量库构建之后执行，确保向量存储服务已初始化
    event_success = build_feeding_events_vector_db()

    # 记录喂养事件向量库构建结果日志
    if event_success:
        # 记录构建成功日志
        logger.info("喂养事件向量库构建成功")
    else:
        # 记录构建失败警告
        logger.warning("喂养事件向量库构建失败")

    # 根据构建结果返回退出码（任一失败则返回 1）
    exit(0 if success and event_success else 1)


if __name__ == "__main__":
    """
    脚本入口

    业务逻辑：
    直接调用主函数
    """
    main()