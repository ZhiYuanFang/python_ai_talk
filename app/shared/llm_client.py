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
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, AsyncGenerator

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from pydantic import BaseModel, Field

from app.config.settings import settings

# 初始化日志记录器
logger = logging.getLogger(__name__)


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
        2. 将消息转换为 langchain 格式
        3. 流式调用 LLM，逐块返回结果
        4. 支持 thinking 模式（胖宝诊疗场景）
        5. 释放 Redis 闸门许可

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            model_config: 模型配置
            system_prompt: 系统提示词（可选）
            thinking_enabled: 是否启用思考模式

        Yields:
            LLMResponse 响应结果（流式返回）
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
                    mode="stream",
                    model_config=model_config,
                    system_prompt=system_prompt,
                    messages=messages,
                    thinking_enabled=thinking_enabled,
                )
                # 开始流式调用
                logger.info(f"开始流式调用 LLM: provider={model_config.provider}, model={model_config.name}, thinking_enabled={thinking_enabled}")

                # 思考内容缓冲区
                thinking_buffer = ""
                # 回答内容缓冲区
                answer_buffer = ""

                # 流式获取响应
                async for chunk in client.astream(langchain_messages):
                    # 获取当前 chunk 的内容
                    chunk_content = chunk.content
                    if chunk_content is None:
                        chunk_content = ""
                    if not isinstance(chunk_content, str):
                        chunk_content = str(chunk_content)

                    # 如果启用了思考模式，尝试分离思考和回答内容
                    if thinking_enabled:
                        # 简单的思考/回答分离逻辑
                        # 实际应用中可能需要根据模型返回格式调整
                        if "[思考]" in chunk_content or "思考：" in chunk_content:
                            # 提取思考内容
                            thinking_part = chunk_content.replace("[思考]", "").replace("思考：", "")
                            thinking_buffer += thinking_part
                            yield LLMResponse(content="", thinking=thinking_part)
                        else:
                            # 剩余内容作为回答
                            answer_buffer += chunk_content
                            yield LLMResponse(content=chunk_content, thinking="")
                    else:
                        # 非思考模式，直接返回内容
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
