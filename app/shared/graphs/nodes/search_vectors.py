"""
向量检索节点

业务说明：
LangGraph 节点：根据用户问题从向量库中检索相关知识。
异常时返回空列表，不中断图的执行流程。

设计思路：
1. 从 State 中读取用户问题（user_input 或 question）
2. 调用 vector_store.search 进行向量检索
3. 异常时返回空列表，记录错误日志
4. 返回 knowledge 更新 State
"""

import logging
from typing import Any, Dict

from app.shared.vector_store import vector_store

# 初始化日志记录器
logger = logging.getLogger(__name__)

# 向量检索默认返回数量
DEFAULT_SEARCH_LIMIT = 5


async def search_vectors(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    向量检索节点函数

    业务逻辑：
    1. 从 State 中读取用户问题（优先 user_input，其次 question）
    2. 调用向量库进行相似性检索
    3. 检索异常时返回空列表，不中断流程
    4. 返回 knowledge 更新 State

    Args:
        state: 当前图状态

    Returns:
        需要更新的 State 字段字典
    """
    # 读取用户问题：intent_graph 用 user_input，clinic_graph 用 question
    query = state.get("user_input") or state.get("question", "")

    if not query:
        # 没有查询词，返回空列表
        return {"knowledge": []}

    try:
        # 调用向量库检索
        results = vector_store.search(
            query=query,
            n_results=DEFAULT_SEARCH_LIMIT,
        )

        # 格式化结果：转换为字典列表
        knowledge = []
        if results and isinstance(results, list):
            for item in results:
                # 兼容不同的返回格式
                if isinstance(item, dict):
                    knowledge.append(item)
                elif isinstance(item, tuple):
                    knowledge.append({
                        "content": item[0] if len(item) > 0 else "",
                        "score": item[1] if len(item) > 1 else 0,
                    })
                else:
                    knowledge.append({"content": str(item), "score": 0})

        return {"knowledge": knowledge}

    except Exception as e:
        # 向量检索失败，返回空列表，不中断流程
        logger.error(f"向量检索失败: {str(e)}")
        return {"knowledge": []}
