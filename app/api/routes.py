"""
API 路由模块

业务说明：
定义所有 HTTP 接口的路由，包括意图分析、胖宝诊疗和健康检查。

设计思路：
1. 使用 FastAPI 的 APIRouter 组织路由
2. 路由函数只负责请求参数验证和响应格式化
3. 业务逻辑委托给服务层处理
4. 添加详细的接口文档注释
"""

import asyncio
import json
import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.schemas.intent import ClinicRequest, IntentRequest, IntentResponse, ModelConfig
from app.services.event_cache import event_cache
from app.services.http_client import http_client
from app.services.llm_client import LLMClient, LLMModelConfig, llm_client
from app.services.vector_store import vector_store

# 初始化日志记录器
logger = logging.getLogger(__name__)

# 创建 API 路由实例
router = APIRouter(prefix="/v1", tags=["AI Talk"])


# ============ 意图分析接口 ============
@router.post("/analyze/intent", response_model=IntentResponse, summary="意图分析")
async def analyze_intent(request: IntentRequest):
    """
    意图分析接口

    业务说明：
    接收用户输入的自然语言文本，分析其意图并返回结构化结果。
    支持的意图类型包括：喂养记录（start/end/one）、历史查询（search）、
    成长建议（suggestion）、对话（reply）、退出（exit）。

    请求参数：
    - text: 用户输入的自然语言文本
    - device_no: 设备编号（用于获取历史数据和宝宝画像）
    - model: 模型配置（提供商、模型名称、最大并发数）

    返回结果：
    - target_type: 目标类型（feeding, history, suggest, conversation, exit）
    - action: 动作类型（start, end, one, search, suggestion, reply, exit）
    - event_name: 事件名称（喂养场景）
    - keywords: 匹配的关键词列表
    - content: 回答内容（对话场景）
    """
    try:
        # 记录请求日志
        logger.info(f"收到意图分析请求: text={request.text[:50]}..., device_no={request.device_no}")

        # 获取事件字典（从缓存或兄弟仓）
        event_dictionary = await event_cache.get_event_dictionary()

        # 构建系统提示词，用于引导 LLM 进行意图分析
        system_prompt = _build_intent_system_prompt(event_dictionary)

        # 构建用户消息，包含用户输入和事件字典信息
        user_message = _build_intent_user_message(request.text, event_dictionary)

        # 调用 LLM 进行意图分析
        # 使用同步调用方式，因为意图分析不需要流式响应
        response = await llm_client.invoke(
            messages=[{"role": "user", "content": user_message}],
            model_config=LLMModelConfig(
                provider=request.model.provider,
                name=request.model.name,
                max_in_flight=request.model.max_in_flight,
            ),
            system_prompt=system_prompt,
        )

        # 解析 LLM 返回的 JSON 结果
        intent_result = _parse_intent_result(response.content)

        # 处理特殊场景
        # 如果是喂养场景且没有匹配到事件名称，尝试从文本中提取
        if intent_result["target_type"] == "feeding" and not intent_result["event_name"]:
            intent_result["event_name"] = _match_event_name(request.text, event_dictionary)

        # 如果是对话场景且没有内容，使用兜底文案
        if intent_result["target_type"] == "conversation" and not intent_result["content"]:
            intent_result["content"] = _get_default_conversation_reply(request.text)

        # 构建响应对象
        return IntentResponse(**intent_result)

    except Exception as e:
        # 记录错误日志
        logger.error(f"意图分析失败: {str(e)}")
        # 抛出 HTTP 500 错误
        raise HTTPException(status_code=500, detail=str(e))


def _build_intent_system_prompt(event_dictionary: List[Dict[str, Any]]) -> str:
    """
    构建意图分析的系统提示词

    业务逻辑：
    将事件字典格式化为系统提示词，引导 LLM 正确识别意图。

    Args:
        event_dictionary: 事件字典列表

    Returns:
        系统提示词字符串
    """
    # 将事件字典转换为字符串格式
    event_str = json.dumps(event_dictionary, ensure_ascii=False, indent=2)

    # 构建系统提示词
    return f"""
你是一个专业的母婴喂养意图分析助手。
请分析用户输入的自然语言文本，识别其意图，并返回结构化的 JSON 结果。

可用的事件类型如下：
{event_str}

意图类型说明：
- feeding: 喂养记录相关意图
  - start: 开始喂养记录（如"开始喂奶"、"开始喂奶粉"）
  - end: 结束喂养记录（如"结束喂奶"、"停止喂奶粉"）
  - one: 单次喂养记录（如"刚才喝了120ml奶粉"）
- history: 历史查询相关意图
  - search: 查询历史记录（如"今天吃了多少"、"上次喂奶是什么时候"）
- suggest: 成长建议相关意图
  - suggestion: 获取成长建议（如"宝宝最近食量怎么样"）
- conversation: 对话交流意图
  - reply: 闲聊对话（如"你好"、"谢谢"）
- exit: 退出意图
  - exit: 退出当前功能（如"退出"、"结束"）

请严格按照以下 JSON 格式返回结果：
{{
    "target_type": "feeding|history|suggest|conversation|exit",
    "action": "start|end|one|search|suggestion|reply|exit",
    "event_name": "匹配到的事件名称（喂养场景必填）",
    "keywords": ["匹配到的关键词列表"],
    "content": "对话场景的回答内容"
}}

注意事项：
1. 如果无法确定意图，请使用 "conversation" + "reply"，并在 content 中说明无法理解
2. 喂养场景必须填写 event_name
3. keywords 列表要包含用户输入中的关键信息
4. 返回结果必须是合法的 JSON 格式
"""


def _build_intent_user_message(text: str, event_dictionary: List[Dict[str, Any]]) -> str:
    """
    构建意图分析的用户消息

    业务逻辑：
    将用户输入和事件字典组合成完整的用户消息。

    Args:
        text: 用户输入的自然语言文本
        event_dictionary: 事件字典列表

    Returns:
        用户消息字符串
    """
    return f"""
请分析以下用户输入，识别其意图：

用户输入：{text}

可用事件类型：{json.dumps([e["event_name"] for e in event_dictionary], ensure_ascii=False)}
"""


def _parse_intent_result(content: str) -> Dict[str, Any]:
    """
    解析 LLM 返回的意图分析结果

    业务逻辑：
    从 LLM 返回的文本中提取 JSON 格式的意图分析结果。

    Args:
        content: LLM 返回的文本内容

    Returns:
        意图分析结果字典
    """
    try:
        # 尝试直接解析 JSON
        return json.loads(content)
    except json.JSONDecodeError:
        # 如果直接解析失败，尝试提取 JSON 部分
        # LLM 可能会在 JSON 前后添加额外的文本
        import re
        # 使用正则表达式提取 JSON 部分
        match = re.search(r'\{[\s\S]*\}', content)
        if match:
            return json.loads(match.group())
        else:
            # 如果无法提取 JSON，返回默认的对话意图
            logger.warning(f"无法解析意图分析结果: {content}")
            return {
                "target_type": "conversation",
                "action": "reply",
                "event_name": "",
                "keywords": [],
                "content": "抱歉，我无法理解您的请求。",
            }


def _match_event_name(text: str, event_dictionary: List[Dict[str, Any]]) -> str:
    """
    根据文本匹配事件名称

    业务逻辑：
    在文本中查找与事件字典中关键词匹配的事件名称。

    Args:
        text: 用户输入的自然语言文本
        event_dictionary: 事件字典列表

    Returns:
        匹配到的事件名称，如果没有匹配返回空字符串
    """
    # 遍历事件字典，查找匹配的事件
    for event in event_dictionary:
        # 获取事件的关键词
        keywords = event.get("keywords", [])
        # 检查文本中是否包含任何关键词
        for keyword in keywords:
            if keyword in text:
                return event["event_name"]

    # 没有匹配到任何事件，返回空字符串
    return ""


def _get_default_conversation_reply(text: str) -> str:
    """
    获取默认对话回复

    业务逻辑：
    根据用户输入返回合适的默认对话回复（兜底文案）。

    Args:
        text: 用户输入的自然语言文本

    Returns:
        默认回复内容
    """
    # 简单的关键词匹配
    if any(keyword in text for keyword in ["你好", "您好", "hello", "hi"]):
        return "您好！我是您的母婴喂养助手，请问有什么可以帮您的？"
    elif any(keyword in text for keyword in ["谢谢", "感谢", "thanks"]):
        return "不客气！如果有任何喂养方面的问题，随时可以问我。"
    elif any(keyword in text for keyword in ["再见", "拜拜", "bye"]):
        return "再见！祝您和宝宝健康快乐！"
    else:
        return "您好！我是专注于母婴喂养领域的智能助手，请问有什么喂养方面的问题我可以帮您解答？"


# ============ 胖宝诊疗接口 ============
@router.post("/clinic/stream", summary="胖宝诊疗流式接口")
async def clinic_stream(request: ClinicRequest):
    """
    胖宝诊疗流式接口

    业务说明：
    接收用户的诊疗问题，返回流式的诊疗建议。
    支持思考模式，先返回思考过程，再返回回答内容。

    请求参数：
    - question: 用户的诊疗问题
    - device_no: 设备编号（用于获取历史数据和宝宝画像）
    - model: 模型配置（提供商、模型名称、最大并发数）

    返回结果：
    流式响应，每个事件包含：
    - type: 消息类型（thinking 或 answer）
    - content: 内容（思考过程或回答内容）
    """
    try:
        # 记录请求日志
        logger.info(f"收到胖宝诊疗请求: question={request.question[:50]}..., device_no={request.device_no}")

        # 并行获取历史数据和宝宝画像
        # 使用 asyncio.gather 提高性能
        history_task = http_client.get_history_events(request.device_no)
        baby_profile_task = http_client.get_baby_profile(request.device_no)
        history_events, baby_profile = await asyncio.gather(history_task, baby_profile_task)

        # 从向量库检索相关知识
        # 使用用户问题作为查询词
        knowledge_results = vector_store.search(request.question, n_results=5)

        # 构建系统提示词
        system_prompt = _build_clinic_system_prompt(baby_profile, history_events, knowledge_results)

        # 构建用户消息
        user_message = request.question

        # 创建流式响应生成器
        async def stream_generator():
            # 流式调用 LLM
            async for chunk in llm_client.stream(
                messages=[{"role": "user", "content": user_message}],
                model_config=LLMModelConfig(
                    provider=request.model.provider,
                    name=request.model.name,
                    max_in_flight=request.model.max_in_flight,
                ),
                system_prompt=system_prompt,
                thinking_enabled=True,
            ):
                # 构建响应事件
                event = {
                    "type": "thinking" if chunk.thinking else "answer",
                    "content": chunk.thinking if chunk.thinking else chunk.content,
                }
                # 转换为 JSON 字符串并添加 SSE 格式
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        # 返回流式响应
        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    except Exception as e:
        # 记录错误日志
        logger.error(f"胖宝诊疗失败: {str(e)}")
        # 抛出 HTTP 500 错误
        raise HTTPException(status_code=500, detail=str(e))


def _build_clinic_system_prompt(
    baby_profile: Dict[str, Any],
    history_events: List[Dict[str, Any]],
    knowledge_results: List[Dict[str, Any]],
) -> str:
    """
    构建胖宝诊疗的系统提示词

    业务逻辑：
    将宝宝画像、历史数据和检索到的知识组合成系统提示词。

    Args:
        baby_profile: 宝宝画像信息
        history_events: 历史事件列表
        knowledge_results: 检索到的知识结果

    Returns:
        系统提示词字符串
    """
    # 格式化宝宝画像
    baby_info = ""
    if baby_profile:
        baby_info = f"""
宝宝信息：
- 生日：{baby_profile.get("birthday", "未知")}
- 性别：{baby_profile.get("gender", "未知")}
"""

    # 格式化历史事件
    history_info = ""
    if history_events:
        # 只取最近 10 条记录
        recent_events = history_events[-10:]
        history_info = f"""
最近喂养记录：
{json.dumps(recent_events, ensure_ascii=False, indent=2)}
"""

    # 格式化检索到的知识
    knowledge_info = ""
    if knowledge_results:
        knowledge_texts = [f"- {r['content']}（相似度：{r['score']}）" for r in knowledge_results]
        knowledge_info = f"""
相关知识：
{"\n".join(knowledge_texts)}
"""

    # 构建系统提示词（复用 go_ai_talk 的 aiClinic.systemPrompt）
    return f"""
你是一个专业的儿科医生助手，擅长处理宝宝喂养和健康问题。

{baby_info}

{history_info}

{knowledge_info}

请根据以上信息，为用户提供专业的诊疗建议。
回答风格：专业、温暖、易懂。
先进行思考，然后给出详细的回答。

思考格式：[思考]你的思考过程...
回答格式：直接给出回答内容。
"""


# ============ 健康检查接口 ============
@router.get("/health", summary="健康检查")
async def health_check():
    """
    健康检查接口

    业务说明：
    用于 Docker healthcheck 和负载均衡器的健康检查。
    返回服务状态信息。

    返回结果：
    - status: 服务状态（healthy 或 unhealthy）
    - version: 服务版本
    """
    return {
        "status": "healthy",
        "version": "0.1.0",
    }