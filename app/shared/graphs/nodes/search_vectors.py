"""
向量检索节点

业务说明：
LangGraph 节点：根据用户问题从向量库中检索相关知识。
检索后按相似度过滤：默认只保留最高分且 score>=门槛的条目（K=1, T=0.6），
不够像则 knowledge 为空，由闺蜜口语陪聊，降低 token。

设计思路：
1. 从 State 中读取用户问题（user_input / question / tip 事件名）
2. 多取若干候选再按 score 排序过滤
3. 写入 State 的 knowledge 即最终进 prompt / 飞轮 ids 的集合
"""

import logging
from typing import Any, Dict, List

from app.config.settings import settings
from app.shared.vector_store import vector_store

logger = logging.getLogger(__name__)

# 底层多取候选，再按门槛与 top_k 收紧（给排序留余地）
DEFAULT_SEARCH_LIMIT = 5


def filter_knowledge_for_prompt(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    按配置收紧进 LLM 的知识列表。

    业务逻辑：
    1. 按 score 降序
    2. 丢弃 score < knowledge_min_score 的条目
    3. 最多保留 knowledge_prompt_top_k 条（默认 1）

    Args:
        results: 检索结果字典列表（含 score）

    Returns:
        过滤后的知识列表（可能为空）
    """
    if not results:
        return []

    min_score = float(settings.knowledge_min_score)
    top_k = max(0, int(settings.knowledge_prompt_top_k))
    if top_k == 0:
        return []

    sorted_items = sorted(
        results,
        key=lambda r: float(r.get("score") or 0.0),
        reverse=True,
    )
    kept: List[Dict[str, Any]] = []
    for item in sorted_items:
        score = float(item.get("score") or 0.0)
        if score < min_score:
            continue
        kept.append(item)
        if len(kept) >= top_k:
            break

    if not kept and sorted_items:
        top = sorted_items[0]
        logger.info(
            "知识未达注入门槛，放弃注入: top_score=%s, min_score=%s",
            top.get("score"),
            min_score,
        )
    elif kept:
        logger.info(
            "知识注入: count=%s, top_score=%s, min_score=%s",
            len(kept),
            kept[0].get("score"),
            min_score,
        )
    return kept


async def search_vectors(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    向量检索节点函数

    业务逻辑：
    1. 读取查询词并检索候选
    2. 过滤为高匹配子集写入 knowledge（供 prompt 与飞轮）
    3. 异常时返回空列表，不中断流程

    Args:
        state: 当前图状态

    Returns:
        需要更新的 State 字段字典
    """
    query = state.get("user_input") or state.get("question", "")
    if not query:
        event_info = state.get("event_info") or {}
        if isinstance(event_info, dict):
            query = event_info.get("event_name") or ""

    if not query:
        return {"knowledge": []}

    try:
        results = vector_store.search(
            query=query,
            n_results=DEFAULT_SEARCH_LIMIT,
        )

        knowledge: List[Dict[str, Any]] = []
        if results and isinstance(results, list):
            for item in results:
                if isinstance(item, dict):
                    knowledge.append(item)
                elif isinstance(item, tuple):
                    knowledge.append({
                        "content": item[0] if len(item) > 0 else "",
                        "score": item[1] if len(item) > 1 else 0,
                    })
                else:
                    knowledge.append({"content": str(item), "score": 0})

        return {"knowledge": filter_knowledge_for_prompt(knowledge)}

    except Exception as e:
        logger.error(f"向量检索失败: {str(e)}")
        return {"knowledge": []}
