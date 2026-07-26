"""
向量匹配节点

业务说明：
将用户输入转换为向量，与 Milvus 中的事件向量进行相似度匹配。
作为意图分析的第一个节点，优先尝试通过向量匹配识别事件。
支持向量索引刷新和事件字典同步。

设计思路：
1. 使用 OpenAI Embedding 服务将文本转换为向量
2. 通过 Milvus 向量库进行相似度搜索
3. 根据置信度阈值决定后续路由：
   - ≥0.95：高置信直接匹配，提取数量后返回，无需 LLM；
   - 0.90~0.95：中置信匹配，需要用户确认；
   - <0.90：低置信，放弃向量结果，降级至 LLM；
"""

import logging
from typing import Any, Dict

from app.feeding.services.event_vector_store import EventVectorStore
from app.feeding.utils.quantity_extractor import extract_quantity_from_text

# 初始化日志记录器
logger = logging.getLogger(__name__)

# 向量匹配的高置信度阈值（≥此值直接匹配，无需 LLM 或确认）
VECTOR_MATCH_HIGH_CONFIDENCE_THRESHOLD = 0.95

# 向量匹配的中等置信度阈值（<此值降级至 LLM，≥此值但 < 高阈值需要确认）
VECTOR_MATCH_MEDIUM_CONFIDENCE_THRESHOLD = 0.90


def match_event_by_vector(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    向量匹配节点

    业务逻辑：
    1. 获取用户输入和事件向量存储实例
    2. 使用 Embedding 服务将文本转换为向量
    3. 在 Milvus 中搜索最相似的事件
    4. 根据置信度阈值决定后续处理：
       - ≥0.95：高置信直接匹配，无需 LLM 或确认
       - 0.90~0.95：中置信匹配，需要用户确认
       - <0.90：低置信，放弃向量结果，降级至 LLM
    5. 如果高置信度匹配且能提取数量，直接返回结果，跳过 LLM

    Args:
        state: 当前图状态，包含用户输入文本、设备编号等信息

    Returns:
        更新后的状态字典，包含向量匹配结果和置信度
    """
    # 业务说明：路由注入的是 user_input；兼容旧字段 text 作 fallback
    text = state.get("user_input") or state.get("text", "")

    # 获取事件向量存储实例
    vector_store = EventVectorStore()

    try:
        # 执行向量搜索（search_events 返回已归一化的 0–1 score）
        results = vector_store.search_events(text, n_results=1)

        if not results or len(results) == 0:
            logger.info(f"向量匹配未找到结果: text={text[:20]}...")
            return {
                "intent_result": {"match_source": "llm"},
                "match_confidence": 0.0,
                "match_source": "llm",
            }

        # 获取最相似的结果；score 已是 0–1 相似度，直接作置信度
        top_result = results[0]
        confidence = float(top_result.get("score", 0.0))

        logger.info(
            f"向量匹配结果: text={text[:20]}..., "
            f"event_id={top_result['id']}, "
            f"confidence={confidence}, "
            f"metadata={top_result.get('metadata', {})}"
        )

        # 从元数据中提取事件信息
        metadata = top_result.get("metadata", {})

        # 提取数量（前置数量提取，避免通用场景请求 LLM 导致接口延迟）
        quantity = extract_quantity_from_text(text)

        # 高置信度（≥0.95）：直接匹配，无需 LLM 或确认
        if confidence >= VECTOR_MATCH_HIGH_CONFIDENCE_THRESHOLD:
            # 高置信度匹配时，提取数量后直接返回，跳过 LLM 调用
            logger.info(
                f"高置信度向量匹配，跳过 LLM: "
                f"confidence={confidence}, quantity={quantity}"
            )
            intent_result = {
                "target_type": "feeding",
                "action": metadata.get("action") or "one",
                "event_name": metadata["event_name"],
                # 存量 Chroma metadata 可能仍为 int，出站统一为 str
                "event_id": "" if metadata.get("event_id") is None else str(metadata["event_id"]),
                "quantity": quantity,
                "keywords": [metadata.get("action", ""), metadata["event_name"]],
                "match_source": "vector",
                "match_confidence": confidence,
            }
            return {
                "intent_result": intent_result,
                "match_confidence": confidence,
                "match_source": "vector",
                "need_confirm": False,
                "matched_vector_id": top_result["id"],
            }

        # 中等置信度（0.90~0.95）：需要用户确认
        elif confidence >= VECTOR_MATCH_MEDIUM_CONFIDENCE_THRESHOLD:
            logger.info(f"中等置信度向量匹配，需要确认: confidence={confidence}")
            intent_result = {
                "target_type": "feeding",
                "action": metadata.get("action") or "one",
                "event_name": metadata["event_name"],
                "event_id": "" if metadata.get("event_id") is None else str(metadata["event_id"]),
                "quantity": quantity,
                "keywords": [metadata.get("action", ""), metadata["event_name"]],
                "match_source": "vector",
                "match_confidence": confidence,
            }
            return {
                "intent_result": intent_result,
                "match_confidence": confidence,
                "match_source": "vector",
                "need_confirm": True,
                "confirm_message": f"您是要记录 {metadata['event_name']} 吗？",
                "matched_vector_id": top_result["id"],
            }

        # 低置信度（<0.90）：放弃向量结果，降级至 LLM
        else:
            logger.info(f"低置信度向量匹配，降级至 LLM: confidence={confidence}")
            return {
                "intent_result": {"match_source": "llm"},
                "match_confidence": confidence,
                "match_source": "llm",
            }

    except Exception as e:
        logger.error(f"向量匹配失败: {e}", exc_info=True)
        # 向量匹配失败时，降级至 LLM
        return {
            "intent_result": {"match_source": "llm"},
            "match_confidence": 0.0,
            "match_source": "llm",
        }
