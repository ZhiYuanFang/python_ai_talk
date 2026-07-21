"""
知识库管理 API

业务说明：
提供知识库的管理接口，支持外部上传 MD 文件动态扩展知识库。
包含文档上传、列表、详情、更新、删除、统计和分类等功能。

设计思路：
1. 使用 FastAPI 的 File 上传功能处理 MD 文件
2. 文档上传后自动切分、Embedding 并写入向量库
3. 支持按分类筛选文档列表
4. 提供统计信息和分类列表接口
5. 使用扩展元数据字段（source、quality_score 等）支持知识飞轮
"""

import logging
import os
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse

from app.shared.vector_store import vector_store

# 初始化日志记录器
logger = logging.getLogger(__name__)

# 创建路由，挂载在 /knowledge 路径下
router = APIRouter(prefix="/knowledge", tags=["知识库管理"])


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
    chunks = []

    if not content.strip():
        return chunks

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
        if len(current_chunk) + len(sentence) > max_tokens and current_chunk:
            chunks.append(current_chunk)
            current_chunk = current_chunk[-100:] + sentence
        else:
            current_chunk += sentence

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


@router.post("/upload")
async def upload_knowledge(
    file: UploadFile = File(...),
    category: str = Query(default="未分类", description="知识分类"),
):
    """
    上传 MD 文件到知识库

    业务逻辑：
    1. 接收上传的 MD/TXT 文件
    2. 读取文件内容
    3. 按句子切分文档（≤512 tokens）
    4. 为每个 chunk 添加扩展元数据（source、quality_score、match_count 等）
    5. Embedding 并写入向量库
    6. 返回文档 ID 和向量数量

    Args:
        file: 上传的文件（支持 .md 和 .txt 格式）
        category: 知识分类，默认"未分类"

    Returns:
        包含 doc_id、file_name、category、vector_count 的 JSON 响应
    """
    # 检查文件格式
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".md", ".txt"]:
        raise HTTPException(status_code=400, detail="只支持 .md 和 .txt 格式的文件")

    # 读取文件内容
    try:
        content = await file.read()
        content = content.decode("utf-8")
    except Exception as e:
        logger.error(f"读取文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail="读取文件失败")

    # 检查文件内容是否为空
    if not content.strip():
        raise HTTPException(status_code=400, detail="文件内容为空")

    # 生成文档 ID
    doc_id = f"doc_{uuid.uuid4().hex[:8]}"
    file_name = file.filename or "unknown.md"

    # 切分文档为 chunks
    chunks = split_document(content)

    # 为每个 chunk 添加元数据并构建文档列表
    documents = []
    for i, chunk in enumerate(chunks):
        metadata = {
            "source": "admin",
            "quality_score": 0.8,
            "match_count": 0,
            "helpful_count": 0,
            "category": category,
            "doc_id": doc_id,
            "file_name": file_name,
            "file_path": f"uploaded/{file_name}",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "chunk_index": i,
            "total_chunks": len(chunks),
        }

        documents.append({
            "id": f"{doc_id}_chunk_{i}",
            "content": chunk,
            "metadata": metadata,
        })

    # 将文档写入向量库
    try:
        vector_store.add_documents(documents)
        logger.info(f"成功上传文档 {file_name}，生成 {len(chunks)} 个向量")
    except Exception as e:
        logger.error(f"写入向量库失败: {str(e)}")
        raise HTTPException(status_code=500, detail="写入向量库失败")

    # 返回成功响应
    return JSONResponse(content={
        "code": 0,
        "message": "上传成功",
        "data": {
            "doc_id": doc_id,
            "file_name": file_name,
            "category": category,
            "vector_count": len(chunks),
        },
    })


@router.get("/list")
async def list_knowledge(
    category: Optional[str] = Query(default=None, description="按分类筛选"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
):
    """
    列出知识库文档

    业务逻辑：
    1. 支持按分类筛选文档
    2. 支持分页查询
    3. 返回文档列表（按 doc_id 去重，每个文档只返回第一个 chunk 的信息）

    Args:
        category: 分类名称，可选
        page: 页码，默认 1
        page_size: 每页数量，默认 20，最大 100

    Returns:
        包含文档列表和分页信息的 JSON 响应
    """
    try:
        # 获取所有文档
        all_docs = vector_store.get_all_documents(category=category)

        # 按 doc_id 去重，只保留每个文档的第一个 chunk
        unique_docs = {}
        for doc in all_docs:
            doc_id = doc["metadata"].get("doc_id", doc["id"])
            if doc_id not in unique_docs:
                unique_docs[doc_id] = doc

        # 转换为列表
        doc_list = list(unique_docs.values())

        # 按创建时间排序（降序）
        doc_list.sort(
            key=lambda x: x["metadata"].get("created_at", ""),
            reverse=True,
        )

        # 分页处理
        total = len(doc_list)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_docs = doc_list[start:end]

        # 构建响应数据
        result = []
        for doc in paginated_docs:
            result.append({
                "doc_id": doc["metadata"].get("doc_id", doc["id"]),
                "file_name": doc["metadata"].get("file_name", ""),
                "category": doc["metadata"].get("category", "未分类"),
                "quality_score": doc["metadata"].get("quality_score", 0.8),
                "match_count": doc["metadata"].get("match_count", 0),
                "helpful_count": doc["metadata"].get("helpful_count", 0),
                "created_at": doc["metadata"].get("created_at", ""),
                "updated_at": doc["metadata"].get("updated_at", ""),
                "total_chunks": doc["metadata"].get("total_chunks", 1),
                "content_preview": doc["content"][:100] + "..." if len(doc["content"]) > 100 else doc["content"],
            })

        return JSONResponse(content={
            "code": 0,
            "message": "success",
            "data": {
                "list": result,
                "total": total,
                "page": page,
                "page_size": page_size,
            },
        })
    except Exception as e:
        logger.error(f"获取文档列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取文档列表失败")


@router.get("/{doc_id}")
async def get_knowledge(doc_id: str):
    """
    获取文档详情

    业务逻辑：
    1. 根据 doc_id 获取所有相关文档（同一原始文档的所有 chunks）
    2. 合并所有 chunks 的内容
    3. 返回完整文档信息

    Args:
        doc_id: 原始文档 ID

    Returns:
        包含文档完整内容和元数据的 JSON 响应
    """
    try:
        # 获取所有相关文档
        docs = vector_store.get_documents_by_doc_id(doc_id)

        if not docs:
            raise HTTPException(status_code=404, detail="文档不存在")

        # 合并所有 chunks 的内容
        full_content = ""
        metadata = docs[0]["metadata"]

        # 按 chunk_index 排序后合并
        docs.sort(key=lambda x: x["metadata"].get("chunk_index", 0))
        for doc in docs:
            full_content += doc["content"] + "\n"

        return JSONResponse(content={
            "code": 0,
            "message": "success",
            "data": {
                "doc_id": doc_id,
                "file_name": metadata.get("file_name", ""),
                "category": metadata.get("category", "未分类"),
                "quality_score": metadata.get("quality_score", 0.8),
                "match_count": metadata.get("match_count", 0),
                "helpful_count": metadata.get("helpful_count", 0),
                "created_at": metadata.get("created_at", ""),
                "updated_at": metadata.get("updated_at", ""),
                "total_chunks": metadata.get("total_chunks", 1),
                "content": full_content.strip(),
            },
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文档详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取文档详情失败")


@router.put("/{doc_id}")
async def update_knowledge(
    doc_id: str,
    content: str,
    category: Optional[str] = Query(default=None, description="知识分类"),
):
    """
    更新文档内容

    业务逻辑：
    1. 删除旧文档的所有 chunks
    2. 重新切分新内容
    3. 重新 Embedding 并写入向量库
    4. 更新元数据（更新时间、分类等）

    Args:
        doc_id: 原始文档 ID
        content: 新的文档内容
        category: 新的分类，可选（不传则保持原分类）

    Returns:
        包含更新结果的 JSON 响应
    """
    try:
        # 检查文档是否存在
        existing_docs = vector_store.get_documents_by_doc_id(doc_id)
        if not existing_docs:
            raise HTTPException(status_code=404, detail="文档不存在")

        # 获取原分类（如果没有传新分类）
        if category is None:
            category = existing_docs[0]["metadata"].get("category", "未分类")

        # 删除旧文档
        vector_store.delete_by_doc_id(doc_id)

        # 检查新内容是否为空
        if not content.strip():
            raise HTTPException(status_code=400, detail="文档内容不能为空")

        # 切分新文档
        chunks = split_document(content)

        # 构建新文档列表
        documents = []
        for i, chunk in enumerate(chunks):
            metadata = {
                "source": "admin",
                "quality_score": 0.8,  # 更新时重置质量分
                "match_count": 0,     # 更新时重置匹配计数
                "helpful_count": 0,   # 更新时重置有用计数
                "category": category,
                "doc_id": doc_id,
                "file_name": existing_docs[0]["metadata"].get("file_name", "unknown.md"),
                "file_path": existing_docs[0]["metadata"].get("file_path", ""),
                "created_at": existing_docs[0]["metadata"].get("created_at", datetime.now().isoformat()),
                "updated_at": datetime.now().isoformat(),
                "chunk_index": i,
                "total_chunks": len(chunks),
            }

            documents.append({
                "id": f"{doc_id}_chunk_{i}",
                "content": chunk,
                "metadata": metadata,
            })

        # 写入新文档
        vector_store.add_documents(documents)

        logger.info(f"成功更新文档 {doc_id}")

        return JSONResponse(content={
            "code": 0,
            "message": "更新成功",
            "data": {
                "doc_id": doc_id,
                "category": category,
                "vector_count": len(chunks),
            },
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新文档失败")


@router.delete("/{doc_id}")
async def delete_knowledge(doc_id: str):
    """
    删除文档

    业务逻辑：
    1. 根据 doc_id 删除所有相关文档（同一原始文档的所有 chunks）
    2. 返回删除结果

    Args:
        doc_id: 原始文档 ID

    Returns:
        包含删除结果的 JSON 响应
    """
    try:
        # 获取要删除的文档数量
        existing_docs = vector_store.get_documents_by_doc_id(doc_id)
        if not existing_docs:
            raise HTTPException(status_code=404, detail="文档不存在")

        # 删除文档
        vector_store.delete_by_doc_id(doc_id)

        logger.info(f"成功删除文档 {doc_id}")

        return JSONResponse(content={
            "code": 0,
            "message": "删除成功",
            "data": {
                "doc_id": doc_id,
                "deleted_count": len(existing_docs),
            },
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除文档失败")


@router.get("/stats")
async def get_knowledge_stats():
    """
    获取知识库统计信息

    业务逻辑：
    1. 获取文档总数
    2. 获取分类数量和各分类文档数
    3. 获取平均质量分
    4. 返回统计信息

    Returns:
        包含统计信息的 JSON 响应
    """
    try:
        stats = vector_store.get_stats()

        return JSONResponse(content={
            "code": 0,
            "message": "success",
            "data": stats,
        })
    except Exception as e:
        logger.error(f"获取统计信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取统计信息失败")


@router.get("/categories")
async def get_knowledge_categories():
    """
    获取所有知识分类

    业务逻辑：
    1. 查询向量库中所有不同的 category
    2. 统计每个分类的文档数量
    3. 返回分类列表

    Returns:
        包含分类列表的 JSON 响应
    """
    try:
        categories = vector_store.get_categories()

        return JSONResponse(content={
            "code": 0,
            "message": "success",
            "data": categories,
        })
    except Exception as e:
        logger.error(f"获取分类列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取分类列表失败")
