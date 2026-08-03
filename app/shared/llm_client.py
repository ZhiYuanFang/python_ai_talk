"""
LLM 客户端封装模块

业务说明：
本模块负责封装对不同 LLM 提供商（DeepSeek、Zhipu）的调用，提供统一的接口。
支持同步和流式调用，用于意图分析和诊疗场景。

设计思路：
1. 使用 langchain-openai 库作为统一接口，通过不同的 base_url 区分提供商
2. 支持动态选择模型，由调用方传入 provider 和 model 参数
3. 实现 Redis 闸门控制，避免超过并发限制
4. 提供统一的错误处理和重试机制
5. 流式 thinking：经底层 OpenAI 客户端读 reasoning_content（ChatOpenAI 会丢该字段）
"""

import logging
from typing import Any, Dict, List, Optional, AsyncGenerator, Tuple

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from pydantic import BaseModel, Field

from app.config.settings import settings

# 初始化日志记录器
logger = logging.getLogger(__name__)

# DeepSeek / 智谱 OpenAI 兼容接口的原生思考开关（经 extra_body 传递）
_THINKING_EXTRA_BODY: Dict[str, Any] = {"thinking": {"type": "enabled"}}


def normalize_llm_provider(provider: str) -> str:
    """
    将调用方传入的 provider 规范为内部权威名。

    业务逻辑：
    1. strip + lower，兼容 Zhipu / ZHIPU 等大小写
    2. zhipu 与 glm 同属智谱，统一为内部名 glm（共用 GLM_* 配置）
    3. deepseek 保持 deepseek；其它原样返回，由 _get_client 拒绝

    Args:
        provider: 请求中的提供商字符串

    Returns:
        规范化后的提供商名（如 glm、deepseek）
    """
    canonical = (provider or "").strip().lower()
    # 智谱别名：Go 常传 zhipu，本仓配置键为 glm
    if canonical == "zhipu":
        return "glm"
    return canonical


def _coerce_text(value: Any) -> str:
    """将 chunk 字段规范为 str；None / 非 str 转为空串或 str()。"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def extract_stream_thinking_and_content(chunk_or_delta: Any) -> Tuple[str, str]:
    """
    从流式 delta / AIMessageChunk 提取 (thinking, content)。

    查找顺序（thinking）：
    1. 顶层 reasoning_content
    2. additional_kwargs.reasoning_content / reasoning
    content 取顶层 content。二者可同时非空。
    """
    thinking = getattr(chunk_or_delta, "reasoning_content", None)
    if thinking is None and isinstance(chunk_or_delta, dict):
        thinking = chunk_or_delta.get("reasoning_content")
    if thinking is None:
        additional = getattr(chunk_or_delta, "additional_kwargs", None)
        if additional is None and isinstance(chunk_or_delta, dict):
            additional = chunk_or_delta.get("additional_kwargs")
        if isinstance(additional, dict):
            thinking = additional.get("reasoning_content") or additional.get("reasoning")

    content = getattr(chunk_or_delta, "content", None)
    if content is None and isinstance(chunk_or_delta, dict):
        content = chunk_or_delta.get("content")

    return _coerce_text(thinking), _coerce_text(content)


def _build_openai_chat_messages(
    messages: List[Dict[str, str]],
    system_prompt: Optional[str],
) -> List[Dict[str, str]]:
    """将本仓消息列表转为 OpenAI chat.completions messages。"""
    openai_messages: List[Dict[str, str]] = []
    if system_prompt:
        openai_messages.append({"role": "system", "content": system_prompt})
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role in ("system", "user", "assistant"):
            openai_messages.append({"role": role, "content": content})
    return openai_messages


class LLMModelConfig(BaseModel):
    """
    LLM 模型配置类

    业务说明：
    用于封装调用 LLM 时的模型配置参数，由 Go 服务传入。
    """
    provider: str = Field(
        ...,
        description="LLM 提供商，可选值: deepseek, glm, zhipu（zhipu 与 glm 等价）",
    )
    name: str = Field(..., description="模型名称")
    max_in_flight: int = Field(3, description="最大并发数")


class LLMResponse(BaseModel):
    """
    LLM 响应结果类

    业务说明：
    封装 LLM 调用的返回结果，包含回答内容和思考过程（如果有）。
    """
    content: str = Field("", description="LLM 回答内容")
    thinking: str = Field("", description="思考过程（流式诊疗场景）")


class LLMClient:
    """
    LLM 客户端类

    业务说明：
    提供统一的 LLM 调用接口，支持 DeepSeek 和 Zhipu 双提供商。
    包含并发控制（Redis 闸门）和错误处理。
    采用延迟初始化模式，import 阶段不连接 Redis，第一次调用时才初始化。
    """

    def __init__(self):
        """
        初始化 LLM 客户端

        业务逻辑：
        1. 延迟初始化 Redis 闸门控制器（第一次调用时才创建）
        2. 创建不同提供商的客户端缓存
        3. 使用线程锁确保并发安全
        """
        # Redis 闸门控制器（延迟初始化，第一次调用时才创建）
        self._redis_gate = None
        # LLM 客户端缓存
        self._clients: Dict[str, ChatOpenAI] = {}
        # 线程锁，用于延迟初始化的并发安全
        import threading
        self._init_lock = threading.Lock()

    def _get_redis_gate(self):
        """
        获取 Redis 闸门控制器（延迟初始化）

        业务逻辑：
        第一次调用时创建 RedisGate 实例，使用双重检查锁定确保并发安全。
        延迟初始化的目的是避免 import 阶段连接外部依赖，提升服务启动健壮性。

        Returns:
            RedisGate 实例
        """
        # 第一次检查：无锁快速路径
        if self._redis_gate is None:
            # 获取锁
            with self._init_lock:
                # 第二次检查：确保只有一个线程创建实例
                if self._redis_gate is None:
                    # 延迟导入，避免循环依赖
                    from app.shared.redis_gate import RedisGate
                    logger.info("延迟初始化 Redis 闸门控制器")
                    self._redis_gate = RedisGate()
        return self._redis_gate

    def _log_request_payload(
        self,
        *,
        mode: str,
        model_config: LLMModelConfig,
        system_prompt: Optional[str],
        messages: List[Dict[str, str]],
        thinking_enabled: Optional[bool] = None,
    ) -> None:
        """
        以 INFO 全量打印即将发送给 LLM 的载荷，便于调试核对。

        Args:
            mode: 调用模式（invoke / stream）
            model_config: 模型配置
            system_prompt: 系统提示词（可选）
            messages: 消息列表
            thinking_enabled: 流式思考开关（仅 stream 时有意义）
        """
        thinking_part = (
            f", thinking_enabled={thinking_enabled}"
            if thinking_enabled is not None
            else ""
        )
        # 统一前缀便于日志检索
        logger.info(
            "--- LLM request payload BEGIN --- "
            f"mode={mode}, provider={model_config.provider}, "
            f"model={model_config.name}{thinking_part}"
        )
        logger.info(
            f"--- LLM request system_prompt ---\n{system_prompt if system_prompt else ''}"
        )
        for i, msg in enumerate(messages):
            role = msg.get("role", "user")
            content = msg.get("content", "")
            logger.info(f"--- LLM request message[{i}] role={role} ---\n{content}")
        logger.info("--- LLM request payload END ---")

    def _log_response_content(
        self,
        *,
        mode: str,
        model_config: LLMModelConfig,
        content: str,
    ) -> None:
        """
        以 INFO 打印 LLM 回复正文，便于与 request payload 对照排查。

        Args:
            mode: 调用模式（invoke / stream）
            model_config: 模型配置
            content: 回复正文（stream 为累积后的 answer）
        """
        text = content if content is not None else ""
        logger.info(
            "--- LLM response BEGIN --- "
            f"mode={mode}, provider={model_config.provider}, "
            f"model={model_config.name}, chars={len(text)}"
        )
        logger.info(f"--- LLM response content ---\n{text}")
        logger.info("--- LLM response END ---")

    def _get_client(self, provider: str, model_name: str) -> ChatOpenAI:
        """
        获取指定提供商的 LLM 客户端

        业务逻辑：
        1. 规范化 provider（zhipu→glm，大小写不敏感）
        2. 用规范名生成缓存 key，使 zhipu/glm 共享同一客户端
        3. 按规范名选择 API Key / Base URL；未知提供商报错

        Args:
            provider: LLM 提供商（deepseek、glm 或 zhipu）
            model_name: 模型名称

        Returns:
            ChatOpenAI 客户端实例
        """
        # 保留原始值仅用于报错提示；选路与缓存一律用规范名
        original_provider = provider
        canonical = normalize_llm_provider(provider)

        # 缓存 key 用规范名，避免 zhipu:model 与 glm:model 各建一份
        cache_key = f"{canonical}:{model_name}"

        if cache_key in self._clients:
            return self._clients[cache_key]

        if canonical == "deepseek":
            api_key = settings.deepseek_api_key
            base_url = settings.deepseek_base_url
        elif canonical == "glm":
            # glm / zhipu 共用智谱配置
            api_key = settings.glm_api_key
            base_url = settings.glm_base_url
        else:
            raise ValueError(f"不支持的 LLM 提供商: {original_provider}")

        if not api_key:
            raise ValueError(f"{canonical} API Key 未配置")

        client = ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=0.7,  # 温度参数，控制输出的随机性
            max_tokens=4096,  # 最大输出 token 数
            timeout=30,  # 请求超时时间（秒）
        )

        self._clients[cache_key] = client

        return client

    async def invoke(
        self,
        messages: List[Dict[str, str]],
        model_config: LLMModelConfig,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """
        同步调用 LLM

        业务逻辑：
        1. 获取 Redis 闸门许可（并发控制）
        2. 将消息转换为 langchain 格式
        3. 调用 LLM 并返回结果
        4. 释放 Redis 闸门许可

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            model_config: 模型配置
            system_prompt: 系统提示词（可选）

        Returns:
            LLMResponse 响应结果
        """
        # 获取 Redis 闸门许可，控制并发数
        async with self._get_redis_gate().acquire(model_config.name, model_config.max_in_flight):
            try:
                # 获取对应的 LLM 客户端
                client = self._get_client(model_config.provider, model_config.name)

                # 构建 langchain 格式的消息列表
                langchain_messages = []

                # 如果提供了系统提示词，添加到消息列表开头
                if system_prompt:
                    langchain_messages.append(SystemMessage(content=system_prompt))

                # 将输入消息转换为 langchain 格式
                for msg in messages:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")

                    if role == "system":
                        langchain_messages.append(SystemMessage(content=content))
                    elif role == "user":
                        langchain_messages.append(HumanMessage(content=content))
                    elif role == "assistant":
                        langchain_messages.append(AIMessage(content=content))

                # INFO 全量打印发送载荷，便于核对实际发给模型的内容
                self._log_request_payload(
                    mode="invoke",
                    model_config=model_config,
                    system_prompt=system_prompt,
                    messages=messages,
                )
                # 调用 LLM
                logger.info(f"开始调用 LLM: provider={model_config.provider}, model={model_config.name}")
                response = await client.ainvoke(langchain_messages)
                content = response.content if response.content is not None else ""
                if not isinstance(content, str):
                    content = str(content)
                # 成功后打印回复正文（失败走 except，不打残缺 response）
                self._log_response_content(
                    mode="invoke",
                    model_config=model_config,
                    content=content,
                )
                return LLMResponse(content=content)

            except Exception as e:
                # 记录错误日志
                logger.error(f"LLM 调用失败: {str(e)}")
                raise

    async def stream(
        self,
        messages: List[Dict[str, str]],
        model_config: LLMModelConfig,
        system_prompt: Optional[str] = None,
        thinking_enabled: bool = False,
    ) -> AsyncGenerator[LLMResponse, None]:
        """
        流式调用 LLM

        业务逻辑：
        1. 获取 Redis 闸门许可（并发控制）
        2. thinking_enabled 时经底层 OpenAI 客户端开启原生思考并映射 reasoning_content
        3. 否则走 ChatOpenAI.astream，仅推送正文
        4. 释放 Redis 闸门许可

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            model_config: 模型配置
            system_prompt: 系统提示词（可选）
            thinking_enabled: 是否启用提供商原生思考模式

        Yields:
            LLMResponse 响应结果（流式返回；thinking 增量不加尾部换行）
        """
        # 获取 Redis 闸门许可，控制并发数
        async with self._get_redis_gate().acquire(model_config.name, model_config.max_in_flight):
            try:
                # 获取对应的 LLM 客户端（缓存实例；thinking 仅在本次 create 传入）
                client = self._get_client(model_config.provider, model_config.name)

                # INFO 全量打印发送载荷，便于核对实际发给模型的内容
                self._log_request_payload(
                    mode="stream",
                    model_config=model_config,
                    system_prompt=system_prompt,
                    messages=messages,
                    thinking_enabled=thinking_enabled,
                )
                # 开始流式调用
                logger.info(
                    f"开始流式调用 LLM: provider={model_config.provider}, "
                    f"model={model_config.name}, thinking_enabled={thinking_enabled}"
                )

                answer_buffer = ""

                if thinking_enabled:
                    # ChatOpenAI.astream 会丢弃非标 reasoning_content，改走底层 OpenAI 流
                    openai_messages = _build_openai_chat_messages(
                        messages, system_prompt
                    )
                    create_kwargs: Dict[str, Any] = {
                        "model": model_config.name,
                        "messages": openai_messages,
                        "stream": True,
                        "temperature": 0.7,
                        "max_tokens": 4096,
                        # 仅本次请求开启；不写回缓存 ChatOpenAI.extra_body
                        "extra_body": dict(_THINKING_EXTRA_BODY),
                    }
                    stream = await client.root_async_client.chat.completions.create(
                        **create_kwargs
                    )
                    async for chunk in stream:
                        if not getattr(chunk, "choices", None):
                            continue
                        delta = chunk.choices[0].delta
                        thinking_part, content_part = extract_stream_thinking_and_content(
                            delta
                        )
                        if not thinking_part and not content_part:
                            continue
                        if content_part:
                            answer_buffer += content_part
                        yield LLMResponse(
                            content=content_part,
                            thinking=thinking_part,
                        )
                else:
                    # 非思考模式：沿用 langchain 消息格式与 astream
                    langchain_messages = []
                    if system_prompt:
                        langchain_messages.append(SystemMessage(content=system_prompt))
                    for msg in messages:
                        role = msg.get("role", "user")
                        content = msg.get("content", "")
                        if role == "system":
                            langchain_messages.append(SystemMessage(content=content))
                        elif role == "user":
                            langchain_messages.append(HumanMessage(content=content))
                        elif role == "assistant":
                            langchain_messages.append(AIMessage(content=content))

                    async for chunk in client.astream(langchain_messages):
                        chunk_content = _coerce_text(chunk.content)
                        if not chunk_content:
                            continue
                        answer_buffer += chunk_content
                        yield LLMResponse(content=chunk_content, thinking="")

                # 流正常结束后打一次累积回答（不打 thinking；不逐 chunk）
                self._log_response_content(
                    mode="stream",
                    model_config=model_config,
                    content=answer_buffer,
                )

            except Exception as e:
                # 记录错误日志
                logger.error(f"LLM 流式调用失败: {str(e)}")
                raise


# 创建全局 LLM 客户端实例
llm_client = LLMClient()
