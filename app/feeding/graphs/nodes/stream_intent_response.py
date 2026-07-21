"""
意图分析流式响应节点

业务说明：
LangGraph 流式响应生成器节点，用于意图分析流程的 SSE 流式输出。
将 intent_graph.astream() 的输出转换为 SSE 格式事件，供前端实时展示思考过程和最终结果。
前端通过接收 thinking 事件显示当前处理进度，接收 answer 事件获取最终意图结果。

设计思路：
1. 接收 intent_graph.astream() 的异步生成器作为输入（updates 模式）
2. 遍历每个节点更新，yield thinking 类型 SSE 事件，附带节点名和对应提示语
3. 累积各节点状态更新到最终状态，提取 intent_result 作为最终回答
4. 节点全部完成后，yield answer 类型 SSE 事件，附带意图结果
5. 最后 yield [DONE] 标记，表示流结束

使用场景：
- 路由层（如 FastAPI 端点）调用意图分析图时，使用此生成器包装 astream 输出
- 前端通过 SSE 协议接收实时思考过程和最终意图结果
- 适用于意图分析流程的流式响应场景（向量匹配、意图分类、用户确认、回答生成等）
"""

# 日志模块导入
import logging
# JSON 序列化模块导入
import json
# 类型提示导入
from typing import Any, AsyncGenerator, Dict

# 意图流式响应 Schema 导入（后续创建，当前仅占位导入）
from app.feeding.schemas.intent import IntentStreamResponse

# 初始化日志记录器
logger = logging.getLogger(__name__)

# 节点对应的思考提示语映射表
NODE_THINKING_MESSAGES: Dict[str, str] = {
    # 向量匹配节点：尝试通过向量匹配识别喂养意图
    "match_event_by_vector": "正在匹配喂养事件...",
    # 意图分类节点：LLM 兜底分类用户意图
    "classify_intent": "正在分析用户意图...",
    # 准备确认节点：构造用户确认请求并中断图执行
    "prepare_confirm": "正在准备确认信息...",
    # 处理反馈节点：处理用户确认或拒绝的反馈
    "handle_feedback": "正在处理用户反馈...",
    # 数据需求判断节点：判断回答所需的数据范围
    "judge_data_requirement": "正在判断数据需求...",
    # 历史拉取节点：拉取历史喂养记录数据
    "fetch_history": "正在拉取历史记录...",
    # 向量检索节点：检索相关知识库内容
    "search_vectors": "正在检索相关知识...",
    # 宝宝画像获取节点：获取宝宝画像信息
    "fetch_baby_profile": "正在获取宝宝画像...",
    # 回答生成节点：调用 LLM 生成最终回答
    "generate_response": "正在生成回答...",
}


async def stream_intent_response(state: Dict[str, Any], graph_stream: AsyncGenerator) -> AsyncGenerator[str, None]:
    """
    意图分析流式响应生成器

    业务逻辑：
    1. 遍历 graph_stream（intent_graph.astream() 的输出，updates 模式）
    2. 对每个节点更新，yield thinking 类型 SSE 事件，附带节点名和思考提示语
    3. 累积各节点状态更新到最终状态
    4. 节点全部完成后，从最终状态提取 intent_result
    5. yield answer 类型 SSE 事件，附带意图结果
    6. 最后 yield [DONE] 标记，表示流结束

    Args:
        state: 当前图状态字典
        graph_stream: intent_graph.astream() 返回的异步生成器

    Yields:
        SSE 格式的字符串，包括 thinking 事件、answer 事件和 [DONE] 标记
    """
    # 初始化最终状态，复制传入的 state 作为基础
    final_state: Dict[str, Any] = dict(state)

    # 遍历图流式输出（每个 chunk 是一个字典，键为节点名，值为该节点的状态更新）
    async for chunk in graph_stream:
        # 遍历 chunk 中的每个节点更新
        for node_name, node_update in chunk.items():
            # 跳过非字典类型的更新（部分节点可能返回 None）
            if not isinstance(node_update, dict):
                # 继续处理下一个更新
                continue
            # 累积状态更新到最终状态
            final_state.update(node_update)

            # 获取节点对应的思考提示语，默认使用通用提示
            thinking_message = NODE_THINKING_MESSAGES.get(node_name, f"正在处理 {node_name}...")

            # 构造 thinking 类型 SSE 事件字典
            thinking_event = {
                # 事件类型为思考
                "type": "thinking",
                # 节点名称
                "node": node_name,
                # 思考提示内容
                "content": thinking_message,
            }
            # 序列化为 JSON 字符串并构造 SSE 格式，yield 给调用方
            yield f"data: {json.dumps(thinking_event, ensure_ascii=False)}\n\n"

    # 节点全部完成，从最终状态提取意图结果
    intent_result = final_state.get("intent_result", {})

    # 构造 answer 类型 SSE 事件字典
    answer_event = {
        # 事件类型为最终回答
        "type": "answer",
        # 内容为意图分析结果
        "content": intent_result,
    }
    # 序列化为 JSON 字符串并构造 SSE 格式，yield 给调用方
    yield f"data: {json.dumps(answer_event, ensure_ascii=False)}\n\n"

    # yield 流结束标记，通知前端流式传输完成
    yield "data: [DONE]\n\n"
