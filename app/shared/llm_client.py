"""
LLM 客户端封装模块

业务说明：
本模块负责封装对不同 LLM 提供商的调用，提供统一的接口。
invoke 与 stream 均只打调用方传入的唯一 model；缺 model 立即失败。
不做跨 provider/name 换模；选型（含 VIP）由 Go 决定，Python 不参与。
保留 Redis 并发闸门等待；不新增同模 LLM N 次重试。

设计思路：
1. 使用 langchain-openai 库作为统一接口，通过不同的 base_url 区分提供商
2. 支持动态选择模型，由调用方传入 provider 和 model 参数
3. 实现 Redis 闸门控制，避免超过并发限制
4. 流式 thinking：经底层 OpenAI 客户端读 reasoning_content（ChatOpenAI 会丢该字段）
"""

from __future__ import annotations

import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.config.settings import settings

# 初始化日志记录器
logger = logging.getLogger(__name__)

# DeepSeek / 智谱 OpenAI 兼容接口的原生思考开关（经 extra_body 传递）
_THINKING_EXTRA_BODY: Dict[str, Any] = {"thinking": {"type": "enabled"}}

# 已接入的提供商（规范名）
_KNOWN_PROVIDERS = frozenset({"deepseek", "glm", "siliconflow", "modelscope"})

# 默认并发上限（与历史默认 max_in_flight 对齐）
_DEFAULT_MAX_IN_FLIGHT = 3


def normalize_llm_provider(provider: str) -> str:
    """
    将调用方传入的 provider 规范为内部权威名。

    业务逻辑：
    1. strip + lower，兼容 Zhipu / ZHIPU 等大小写
    2. zhipu 与 glm 同属智谱，统一为内部名 glm（共用 GLM_* 配置）
    3. deepseek / siliconflow / modelscope 保持规范小写名

    Args:
        provider: 请求中的提供商字符串

    Returns:
        规范化后的提供商名（如 glm、deepseek、siliconflow）
    """
    canonical = (provider or "").strip().lower()
    # 智谱别名：Go 常传 zhipu，本仓配置键为 glm
    if canonical == "zhipu":
        return "glm"
    return canonical


def _provider_api_key(canonical: str) -> str:
    """读取规范提供商对应的 API Key（可能为空串）。"""
    if canonical == "deepseek":
        return (settings.deepseek_api_key or "").strip()
    if canonical == "aliyun_dashscope":
        return (settings.aliyun_dashscope_api_key or "").strip()
    if canonical == "glm":
        return (settings.glm_api_key or "").strip()
    if canonical == "siliconflow":
        return (settings.siliconflow_api_key or "").strip()
    if canonical == "modelscope":
        return (settings.modelscope_api_key or "").strip()
    return ""


def _provider_base_url(canonical: str) -> str:
    """读取规范提供商对应的 Base URL。"""
    if canonical == "deepseek":
        return settings.deepseek_base_url
    if canonical == "glm":
        return settings.glm_base_url
    if canonical == "siliconflow":
        return settings.siliconflow_base_url
    if canonical == "modelscope":
        return settings.modelscope_base_url
    if canonical == "aliyun_dashscope":
        return settings.aliyun_dashscope_base_url
    return ""


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


def _build_langchain_messages(
    messages: List[Dict[str, str]],
    system_prompt: Optional[str],
) -> list:
    """组装 langchain 消息列表（system + 多轮）。"""
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
    return langchain_messages


class LLMModelConfig(BaseModel):
    """
    LLM 模型配置类

    业务说明：
    封装调用 LLM 时的模型配置参数，由 Go 服务传入；Python 不换模、不按 VIP 选型。
    """

    provider: str = Field(
        ...,
        description=(
            "LLM 提供商: deepseek, glm, zhipu, siliconflow, modelscope"
            "（zhipu 与 glm 等价）"
        ),
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


def llm_model_config_from_mapping(raw: Any) -> Optional[LLMModelConfig]:
    """
    从 state / 请求 dict 解析模型；缺省或字段不全返回 None（调用方须自行失败）。

    Args:
        raw: 通常为 {"provider","name","max_in_flight"} 或空

    Returns:
        LLMModelConfig 或 None
    """
    if not isinstance(raw, dict):
        return None
    provider = str(raw.get("provider") or "").strip()
    name = str(raw.get("name") or "").strip()
    if not provider or not name:
        return None
    try:
        max_in_flight = int(raw.get("max_in_flight") or _DEFAULT_MAX_IN_FLIGHT)
    except (TypeError, ValueError):
        max_in_flight = _DEFAULT_MAX_IN_FLIGHT
    return LLMModelConfig(
        provider=provider,
        name=name,
        max_in_flight=max_in_flight,
    )


class LLMClient:
    """
    LLM 客户端类

    业务说明：
    提供统一的 LLM 调用接口；支持多提供商，单次唯一 model，不换模。
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
        if self._redis_gate is None:
            with self._init_lock:
                if self._redis_gate is None:
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

    def _require_model_config(
        self, model_config: Optional[LLMModelConfig]
    ) -> LLMModelConfig:
        """
        校验并规范化唯一 model；缺省或不完整则抛错（不换模、无默认单模）。
        """
        if model_config is None:
            raise ValueError("必须传入 model（Go 选型），Python 不换模、无默认单模")
        provider = normalize_llm_provider(model_config.provider)
        name = (model_config.name or "").strip()
        if not provider or not name:
            raise ValueError("model 须含 provider 与 name")
        return LLMModelConfig(
            provider=provider,
            name=name,
            max_in_flight=int(model_config.max_in_flight or _DEFAULT_MAX_IN_FLIGHT),
        )

    def _get_client(self, provider: str, model_name: str) -> ChatOpenAI:
        """
        获取指定提供商的 LLM 客户端

        业务逻辑：
        1. 规范化 provider（zhipu→glm，大小写不敏感）
        2. 用规范名生成缓存 key
        3. 按规范名选择 API Key / Base URL；未知提供商报错

        Args:
            provider: LLM 提供商
            model_name: 模型名称

        Returns:
            ChatOpenAI 客户端实例
        """
        original_provider = provider
        canonical = normalize_llm_provider(provider)
        cache_key = f"{canonical}:{model_name}"

        if cache_key in self._clients:
            return self._clients[cache_key]

        if canonical not in _KNOWN_PROVIDERS:
            raise ValueError(f"不支持的 LLM 提供商: {original_provider}")

        api_key = _provider_api_key(canonical)
        base_url = _provider_base_url(canonical)
        if not api_key:
            raise ValueError(f"{canonical} API Key 未配置")

        client = ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=0.7,
            max_tokens=4096,
            timeout=60,
            max_retries=0,
        )
        self._clients[cache_key] = client
        return client

    async def _invoke_once(
        self,
        messages: List[Dict[str, str]],
        model_config: LLMModelConfig,
        system_prompt: Optional[str],
    ) -> LLMResponse:
        """单次 invoke（含闸门）；失败直接上抛，不换模。"""
        async with self._get_redis_gate().acquire(
            model_config.name, model_config.max_in_flight
        ):
            client = self._get_client(model_config.provider, model_config.name)
            langchain_messages = _build_langchain_messages(messages, system_prompt)
            self._log_request_payload(
                mode="invoke",
                model_config=model_config,
                system_prompt=system_prompt,
                messages=messages,
            )
            logger.info(
                "开始调用 LLM: provider=%s, model=%s",
                model_config.provider,
                model_config.name,
            )
            response = await client.ainvoke(langchain_messages)
            content = response.content if response.content is not None else ""
            if not isinstance(content, str):
                content = str(content)
            self._log_response_content(
                mode="invoke",
                model_config=model_config,
                content=content,
            )
            return LLMResponse(content=content)

    async def invoke(
        self,
        messages: List[Dict[str, str]],
        model_config: Optional[LLMModelConfig] = None,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """
        同步调用 LLM（唯一 model，不换模）

        业务逻辑：
        1. 必须传入可用 model_config（Go 选型）
        2. 仅对该 model 发起一次 invoke；失败直接上抛
        3. 不切换其它 provider/name

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            model_config: 唯一模型；None / 缺字段则报错
            system_prompt: 系统提示词（可选）

        Returns:
            LLMResponse 响应结果
        """
        cfg = self._require_model_config(model_config)
        try:
            return await self._invoke_once(messages, cfg, system_prompt)
        except Exception as e:
            logger.error(
                "LLM 调用失败: provider=%s model=%s err=%s",
                cfg.provider,
                cfg.name,
                str(e),
            )
            raise

    async def _stream_once(
        self,
        messages: List[Dict[str, str]],
        model_config: LLMModelConfig,
        system_prompt: Optional[str],
        thinking_enabled: bool,
    ) -> AsyncGenerator[LLMResponse, None]:
        """
        单次 stream；成功结束后打累积日志。

        Yields:
            LLMResponse 增量
        """
        async with self._get_redis_gate().acquire(
            model_config.name, model_config.max_in_flight
        ):
            client = self._get_client(model_config.provider, model_config.name)
            self._log_request_payload(
                mode="stream",
                model_config=model_config,
                system_prompt=system_prompt,
                messages=messages,
                thinking_enabled=thinking_enabled,
            )
            logger.info(
                "开始流式调用 LLM: provider=%s, model=%s, thinking_enabled=%s",
                model_config.provider,
                model_config.name,
                thinking_enabled,
            )

            answer_buffer = ""
            if thinking_enabled:
                openai_messages = _build_openai_chat_messages(messages, system_prompt)
                create_kwargs: Dict[str, Any] = {
                    "model": model_config.name,
                    "messages": openai_messages,
                    "stream": True,
                    "temperature": 0.7,
                    "max_tokens": 4096,
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
                langchain_messages = _build_langchain_messages(messages, system_prompt)
                async for chunk in client.astream(langchain_messages):
                    chunk_content = _coerce_text(chunk.content)
                    if not chunk_content:
                        continue
                    answer_buffer += chunk_content
                    yield LLMResponse(content=chunk_content, thinking="")

            self._log_response_content(
                mode="stream",
                model_config=model_config,
                content=answer_buffer,
            )

    async def stream(
        self,
        messages: List[Dict[str, str]],
        model_config: Optional[LLMModelConfig] = None,
        system_prompt: Optional[str] = None,
        thinking_enabled: bool = False,
    ) -> AsyncGenerator[LLMResponse, None]:
        """
        流式调用 LLM（唯一 model，不换模）

        业务逻辑：
        1. 必须传入可用 model_config（Go 必带）
        2. 仅对该 model 发起一次 stream；失败直接上抛
        3. 不切换其它 provider/name

        Args:
            messages: 消息列表
            model_config: 唯一模型；None / 缺字段则报错
            system_prompt: 系统提示词（可选）
            thinking_enabled: 是否启用提供商原生思考模式

        Yields:
            LLMResponse 响应结果（流式返回；thinking 增量不加尾部换行）
        """
        cfg = self._require_model_config(model_config)
        try:
            async for item in self._stream_once(
                messages, cfg, system_prompt, thinking_enabled
            ):
                yield item
        except Exception as e:
            logger.error(
                "LLM 流式调用失败: provider=%s model=%s err=%s",
                cfg.provider,
                cfg.name,
                str(e),
            )
            raise


# 创建全局 LLM 客户端实例
llm_client = LLMClient()
