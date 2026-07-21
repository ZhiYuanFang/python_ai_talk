"""
意图分析路由

业务说明：
提供 /v1/analyze/intent 接口，接收自然语言文本和设备编号，返回意图分析结果。
提供 /v1/analyze/intent/stream 接口，以 SSE 流式方式返回意图分析结果和节点思考进度。
使用 LangGraph 的 intent_graph 编排意图分析流程：
1. 向量匹配（优先使用向量数据库匹配喂养事件）
2. 意图分类（向量匹配失败时调用 LLM）
3. 条件路由（根据意图类型）
4. 后处理（history/suggest 意图需要拉取历史、检索向量库、生成回答）
5. 喂养意图确认流程：当置信度在90%-95%之间或LLM解析时，返回 need_confirm=True
6. 内部调用 clinic agent：conversation/suggest 意图自动调用 clinic graph 获取回答

设计思路：
1. 构建 IntentState 初始状态
2. 获取事件字典并注入 state
3. 调用 intent_graph.invoke() 执行流程（非流式）或 astream()（流式）
4. 从最终状态提取意图结果，构建 IntentResponse
5. history/suggest 意图将 LLM 生成的回答填入 content 字段
6. 喂养意图 need_confirm=True 时，客户端需调用确认接口完成意图确认
7. 流式模式通过 SSE 返回 thinking 事件（节点思考进度）和 answer 事件（最终结果）
"""

import json
import logging
# uuid4 导入，用于生成 thread_id（等同于 conversation_id）
from uuid import uuid4
from typing import Any, AsyncGenerator, Dict

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.feeding.graphs.intent_graph import intent_graph
# 导入意图分析请求和响应模型
from app.feeding.schemas.intent import IntentRequest, IntentResponse, IntentStreamResponse
# 导入用户确认反馈请求模型
from app.feeding.schemas.intent import ConfirmFeedbackRequest
from app.feeding.services.event_cache import event_cache
# 导入意图分析节点的思考文案映射
from app.feeding.graphs.nodes.thinking_messages import get_thinking_message


def _extract_interrupt_info(final_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    从图执行后的状态中提取 interrupt 信息

    业务说明：
    LangGraph 的 interrupt() 调用后，ainvoke/astream 返回的状态会包含 __interrupt__ 字段。
    该字段是一个列表，每个元素是一个 Interrupt 对象，其 .value 属性包含 interrupt() 的参数。
    本函数从中提取 need_confirm、confirm_message、conversation_id。

    Args:
        final_state: 图执行后的最终状态

    Returns:
        包含 need_confirm、confirm_message、conversation_id 的字典；
        如果未中断，返回空字典
    """
    # 获取 __interrupt__ 字段，默认为空列表
    interrupts = final_state.get("__interrupt__", [])
    # 如果没有中断信息，返回空字典
    if not interrupts:
        return {}
    try:
        # 取第一个中断对象的 value 属性（即 interrupt() 的参数）
        interrupt_value = interrupts[0].value
        # 如果 value 是字典，直接返回；否则返回空字典
        if isinstance(interrupt_value, dict):
            return interrupt_value
        return {}
    except (IndexError, AttributeError, TypeError):
        # 异常时返回空字典
        return {}

# 初始化日志记录器
logger = logging.getLogger(__name__)

# 创建路由实例
router = APIRouter(prefix="/analyze", tags=["意图分析"])


def _build_intent_response(intent_result: Dict[str, Any]) -> IntentResponse:
    """
    从意图结果字典构建 IntentResponse 响应对象

    业务逻辑：
    将图执行后得到的 intent_result 字典映射为 IntentResponse Pydantic 模型。
    确保所有新增字段（quantity、event_type、event_unit、is_new_event、match_confidence、match_source）
    都正确传递给 Go 侧。

    Args:
        intent_result: 图节点返回的意图结果字典

    Returns:
        IntentResponse 响应对象
    """
    return IntentResponse(
        target_type=intent_result.get("target_type", "conversation"),
        action=intent_result.get("action", "reply"),
        event_name=intent_result.get("event_name", ""),
        event_id=intent_result.get("event_id", ""),
        quantity=intent_result.get("quantity"),
        event_type=intent_result.get("event_type"),
        event_unit=intent_result.get("event_unit"),
        is_new_event=intent_result.get("is_new_event", False),
        keywords=intent_result.get("keywords", []),
        content=intent_result.get("content", ""),
        events=intent_result.get("events", []),
        match_confidence=intent_result.get("match_confidence"),
        match_source=intent_result.get("match_source"),
    )


@router.post("/intent", response_model=IntentResponse, summary="意图分析")
async def analyze_intent(request: IntentRequest):
    """
    意图分析接口（非流式）

    业务逻辑：
    1. 接收用户输入文本、设备编号和模型配置
    2. 从缓存获取事件字典
    3. 构建 IntentState 初始状态
    4. 调用 LangGraph 的 intent_graph 执行完整意图分析流程
    5. 从最终状态提取结果，构建 IntentResponse
    6. history/suggest 意图的回答从 state.response 中获取

    Args:
        request: 意图分析请求，包含 text、deviceNo、model、stream

    Returns:
        IntentResponse 意图分析结果
    """
    # 记录请求日志
    logger.info(
        f"意图分析请求: device_no={request.device_no}, text={request.text[:50]}..."
    )

    # 1. 获取事件字典
    # 业务说明：事件字典用于 LLM 识别事件类型，24 小时 TTL 缓存
    event_dictionary = await event_cache.get_event_dictionary()

    # 2. 构建初始状态
    # 业务说明：将请求参数和事件字典注入 State
    initial_state: Dict[str, Any] = {
        "user_input": request.text,
        "device_no": request.device_no,
        "model_config": {
            "provider": request.model.provider,
            "name": request.model.name,
            "max_in_flight": request.model.max_in_flight,
        },
        "event_dictionary": event_dictionary,
    }

    # 3. 生成 thread_id（等同于 conversation_id）
    # 业务说明：thread_id 用于 LangGraph 的 MemorySaver 检查点，
    # 当 prepare_confirm 调用 interrupt() 时，状态会保存到 MemorySaver[thread_id]
    # 客户端调用 confirm 接口时传入 conversation_id，路由层用它恢复检查点
    thread_id = str(uuid4())

    # 将 thread_id 作为 conversation_id 注入 initial_state
    # 业务说明：prepare_confirm 节点从 state 读取 conversation_id，
    # 传给 interrupt()，客户端通过 interrupt_info 拿到 conversation_id
    initial_state["conversation_id"] = thread_id

    # 4. 调用 LangGraph 执行意图分析流程，传入 thread_id 支持中断恢复
    # 业务说明：
    # - 第一步：向量匹配（优先使用向量数据库匹配喂养事件）
    # - 第二步：意图分类（向量匹配失败时调用 LLM）
    # - feeding/conversation/exit：直接返回或调用 clinic agent
    # - history：判断数据需求→拉取历史→生成回答
    # - suggest：判断数据需求→拉取历史→向量检索→宝宝画像→生成建议
    # - prepare_confirm 调用 interrupt() 时，图执行暂停，ainvoke 返回中断状态
    final_state = await intent_graph.ainvoke(initial_state, thread_id=thread_id)

    # 5. 检查是否被 interrupt 中断（用户需要确认喂养意图）
    # 业务说明：如果图被 interrupt，从 __interrupt__ 字段提取确认信息
    interrupt_info = _extract_interrupt_info(final_state)

    # 6. 从最终状态提取意图结果
    intent_result = final_state.get("intent_result", {})

    # 7. 构建响应
    # 业务说明：history/suggest 意图需要将生成的回答填入 content 字段
    # 多事件场景：将 events 列表填入响应
    response = _build_intent_response(intent_result)

    # 8. 如果被 interrupt 中断，设置确认标记和会话 ID
    # 业务说明：interrupt_info 包含 need_confirm、confirm_message、conversation_id
    # 客户端拿到这些信息后展示确认弹窗，用户确认后调用 confirm 接口恢复图执行
    if interrupt_info:
        # 设置需要确认标记
        response.need_confirm = True
        # 设置确认话术，供客户端展示
        response.confirm_message = interrupt_info.get("confirm_message", "")
        # 设置会话 ID（等同于 thread_id），供客户端调用 confirm 接口时使用
        # 业务说明：优先用 interrupt_info 中的 conversation_id，回退到路由层生成的 thread_id
        response.conversation_id = interrupt_info.get("conversation_id", thread_id)

    # 9. 如果是 history 或 suggest 意图，将 LLM 生成的回答填入 content
    # 业务说明：
    # - history/suggest 意图走了后处理链路，回答在 state.response 中
    # - 其他意图的 content 已经在 intent_result 中（如 conversation 兜底文案）
    target_type = intent_result.get("target_type", "")
    if target_type in ("history", "suggest"):
        llm_response = final_state.get("response", "")
        if llm_response:
            response.content = llm_response

    # 记录响应日志
    logger.info(
        f"意图分析结果: target_type={response.target_type}, "
        f"action={response.action}, "
        f"event_id={response.event_id}, "
        f"quantity={response.quantity}, "
        f"is_new_event={response.is_new_event}"
    )

    return response


@router.post("/intent/stream", summary="意图分析（流式）")
async def analyze_intent_stream(request: IntentRequest):
    """
    意图分析流式接口

    业务逻辑：
    1. 接收用户输入文本、设备编号和模型配置
    2. 从缓存获取事件字典
    3. 构建 IntentState 初始状态
    4. 使用 intent_graph.astream() 流式执行图，每个节点完成时推送 thinking 事件
    5. 所有节点完成后，推送 answer 事件包含最终意图结果
    6. 推送 [DONE] 结束标记

    Args:
        request: 意图分析请求，包含 text、deviceNo、model

    Returns:
        SSE 流式响应，包含 thinking（节点思考进度）和 answer（最终意图结果）两种事件类型
    """
    # 记录请求日志
    logger.info(
        f"意图分析流式请求: device_no={request.device_no}, text={request.text[:50]}..."
    )

    # 1. 获取事件字典
    # 业务说明：事件字典用于向量匹配和 LLM 识别事件类型
    event_dictionary = await event_cache.get_event_dictionary()

    # 2. 构建初始状态
    initial_state: Dict[str, Any] = {
        "user_input": request.text,
        "device_no": request.device_no,
        "model_config": {
            "provider": request.model.provider,
            "name": request.model.name,
            "max_in_flight": request.model.max_in_flight,
        },
        "event_dictionary": event_dictionary,
    }

    # 3. 生成 thread_id（等同于 conversation_id）
    # 业务说明：thread_id 用于 LangGraph 的 MemorySaver 检查点，
    # 流式接口同样需要传 thread_id，支持 prepare_confirm 的 interrupt 中断恢复
    thread_id = str(uuid4())

    # 将 thread_id 作为 conversation_id 注入 initial_state
    # 业务说明：prepare_confirm 节点从 state 读取 conversation_id，
    # 传给 interrupt()，客户端通过 interrupt_info 拿到 conversation_id
    initial_state["conversation_id"] = thread_id

    # 4. 生成 SSE 流式响应
    # 业务说明：使用 StreamingResponse 返回 SSE 格式数据
    # 流式过程包含：节点级 thinking 事件 → answer 事件 → [DONE]
    return StreamingResponse(
        _stream_intent_response(initial_state, thread_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _stream_intent_response(
    initial_state: Dict[str, Any],
    thread_id: str,
) -> AsyncGenerator[str, None]:
    """
    生成意图分析流式 SSE 响应（含节点级 thinking 事件）

    业务逻辑：
    1. 调用 intent_graph.astream() 流式执行图，每个节点完成时推送 thinking 事件
    2. 累积最终状态（意图结果、确认信息等）
    3. 图执行完成后，检查是否被 interrupt 中断
    4. 推送 answer 事件包含最终意图结果（或确认请求）
    5. 推送 [DONE] 结束标记

    interrupt 处理说明：
    - 当 prepare_confirm 调用 interrupt() 时，astream 会自然停止 yield
    - 遍历结束后，从 final_state 检测 __interrupt__ 字段
    - 如果被中断，answer 事件包含 need_confirm=True 和 confirm_message
    - 客户端拿到确认信息后展示弹窗，用户确认后调用 confirm 接口恢复图执行

    Args:
        initial_state: 初始状态字典（含 user_input、device_no、model_config、event_dictionary）
        thread_id: 线程 ID（等同于 conversation_id），用于 MemorySaver 检查点

    Yields:
        SSE 格式的字符串
    """
    # 累积最终状态的字典
    # 业务说明：astream 模式下每个节点返回增量更新，需要手动合并
    final_state: Dict[str, Any] = dict(initial_state)

    # 1. 流式执行 intent_graph，推送节点级 thinking 事件
    # 业务说明：astream(stream_mode="updates") 在每个节点完成时 yield 该节点的更新
    # LangGraph 0.2.x 的 updates 模式 chunk 格式为 {node_name: node_output}（字典）
    # 某些版本或子图场景下可能为 (namespace, {node_name: node_output})（元组）
    # 传入 thread_id 支持中断恢复（prepare_confirm 调用 interrupt 时状态保存到检查点）
    async for chunk in intent_graph.astream(
        initial_state, stream_mode="updates", thread_id=thread_id
    ):
        # 统一解析为 {node_name: node_output} 形式的更新字典
        # 业务说明：无论 chunk 是 dict 还是 tuple，最终都归一化为节点更新字典
        updates_map: Dict[str, Any] = {}

        if isinstance(chunk, tuple) and len(chunk) >= 2:
            # 元组格式：(namespace, {node_name: node_output})
            # 业务说明：namespace 通常是空元组（根图），第二个元素才是节点更新字典
            second = chunk[1]
            if isinstance(second, dict):
                updates_map = second
        elif isinstance(chunk, dict):
            # 字典格式：{node_name: node_output}
            updates_map = chunk

        # 遍历节点更新字典，为每个节点推送 thinking 事件
        for node_name, node_update in updates_map.items():
            # 推送该节点的 thinking 事件
            # 业务说明：每个节点完成时推送一条思考进度，让用户实时感知 AI 工作状态
            thinking_text = get_thinking_message(node_name)
            # 构建 thinking 事件
            event = IntentStreamResponse(
                type="thinking",
                content=thinking_text,
                node=node_name,
            )
            yield f"data: {json.dumps(event.model_dump(), ensure_ascii=False)}\n\n"

            # 累积状态更新到 final_state
            # 业务说明：node_update 是该节点返回的状态更新字典，合并到最终状态
            if isinstance(node_update, dict):
                final_state.update(node_update)

    # 2. 从最终状态提取意图结果
    intent_result = final_state.get("intent_result", {})

    # 3. 构建最终意图响应
    # 多事件场景：将 events 列表填入响应
    response = _build_intent_response(intent_result)

    # 4. 检查是否被 interrupt 中断（用户需要确认喂养意图）
    # 业务说明：astream 遇到 interrupt 会自然停止 yield，遍历结束后检查 __interrupt__ 字段
    interrupt_info = _extract_interrupt_info(final_state)
    if interrupt_info:
        # 设置确认标记和确认话术
        response.need_confirm = True
        response.confirm_message = interrupt_info.get("confirm_message", "")
        # 设置会话 ID，优先用 interrupt_info 中的，回退到路由层生成的 thread_id
        response.conversation_id = interrupt_info.get("conversation_id", thread_id)

    # 5. 如果是 history 或 suggest 意图，将 LLM 回答填入 content
    target_type = intent_result.get("target_type", "")
    if target_type in ("history", "suggest"):
        llm_response = final_state.get("response", "")
        if llm_response:
            response.content = llm_response

    # 6. 推送 answer 事件，包含最终意图结果（或确认请求）
    answer_event = IntentStreamResponse(
        type="answer",
        content=json.dumps(response.model_dump(), ensure_ascii=False),
    )
    yield f"data: {json.dumps(answer_event.model_dump(), ensure_ascii=False)}\n\n"

    # 7. 流式结束标记
    yield "data: [DONE]\n\n"


@router.post("/intent/confirm", response_model=IntentResponse, summary="意图确认反馈")
async def confirm_intent(request: ConfirmFeedbackRequest):
    """
    意图确认反馈接口

    业务逻辑：
    1. 接收用户的确认反馈（confirm 或 reject）
    2. 使用 conversation_id 恢复之前中断的意图图执行
    3. 根据用户反馈继续执行后续流程
    4. 返回最终的意图分析结果

    Args:
        request: 确认反馈请求，包含 conversation_id 和 user_feedback

    Returns:
        IntentResponse 意图分析结果
    """
    # 记录确认反馈请求日志
    logger.info(
        f"意图确认反馈请求: conversation_id={request.conversation_id}, "
        f"user_feedback={request.user_feedback}"
    )

    # 1. 调用意图图的 confirm_intent 方法恢复中断的执行
    # 业务说明：使用 conversation_id（等同于 thread_id）从 MemorySaver 检查点恢复图状态
    # confirm_intent 内部用 Command(resume=user_feedback) 恢复 prepare_confirm 中的 interrupt
    # 图从 prepare_confirm 处继续执行，经过 handle_feedback 节点处理数据飞轮/删除向量
    final_state = await intent_graph.confirm_intent(
        conversation_id=request.conversation_id,
        user_feedback=request.user_feedback,
    )

    # 2. 从最终状态提取意图结果
    intent_result = final_state.get("intent_result", {})

    # 3. 构建响应
    # 多事件场景：将 events 列表填入响应
    response = _build_intent_response(intent_result)

    # 4. 如果是 history 或 suggest 意图，将 LLM 生成的回答填入 content
    # 业务说明：确认后可能路由到 history/suggest 后处理链路
    target_type = intent_result.get("target_type", "")
    if target_type in ("history", "suggest"):
        # 从状态中获取 LLM 生成的回答
        llm_response = final_state.get("response", "")
        if llm_response:
            # 将 LLM 回答填入响应的 content 字段
            response.content = llm_response

    # 记录确认反馈响应日志
    logger.info(
        f"意图确认反馈结果: target_type={response.target_type}, "
        f"action={response.action}"
    )

    # 返回最终意图分析结果
    return response
