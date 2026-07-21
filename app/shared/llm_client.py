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
from app.shared.redis_gate import RedisGate

# 初始化日志记录器
logger = logging.getLogger(__name__)


class LLMModelConfig(BaseModel):
    """
    LLM 模型配置类

    业务说明：
    用于封装调用 LLM 时的模型配置参数，由 Go 服务传入。
    """
    provider: str = Field(..., description="LLM 提供商，可选值: deepseek, glm")
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
    """

    def __init__(self):
        """
        初始化 LLM 客户端

        业务逻辑：
        1. 初始化 Redis 闸门控制器，用于并发控制
        2. 创建不同提供商的客户端缓存
        """
        self.redis_gate = RedisGate()
        self._clients: Dict[str, ChatOpenAI] = {}

    def _get_client(self, provider: str, model_name: str) -> ChatOpenAI:
        """
        获取指定提供商的 LLM 客户端

        业务逻辑：
        1. 根据 provider 选择对应的 API Key 和 Base URL
        2. 如果客户端已缓存，直接返回
        3. 如果未缓存，创建新的客户端并缓存

        Args:
            provider: LLM 提供商（deepseek 或 glm）
            model_name: 模型名称

        Returns:
            ChatOpenAI 客户端实例
        """
        # 生成缓存 key，格式为 provider:model_name
        cache_key = f"{provider}:{model_name}"

        # 如果客户端已缓存，直接返回
        if cache_key in self._clients:
            return self._clients[cache_key]

        # 根据 provider 设置对应的 API Key 和 Base URL
        if provider == "deepseek":
            api_key = settings.deepseek_api_key
            base_url = settings.deepseek_base_url
        elif provider == "glm":
            api_key = settings.glm_api_key
            base_url = settings.glm_base_url
        else:
            raise ValueError(f"不支持的 LLM 提供商: {provider}")

        # 验证 API Key 是否已配置
        if not api_key:
            raise ValueError(f"{provider} API Key 未配置")

        # 创建 ChatOpenAI 客户端
        client = ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=0.7,  # 温度参数，控制输出的随机性
            max_tokens=4096,  # 最大输出 token 数
            timeout=30,  # 请求超时时间（秒）
        )

        # 缓存客户端实例
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
        async with self.redis_gate.acquire(model_config.name, model_config.max_in_flight):
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

                # 调用 LLM
                logger.info(f"开始调用 LLM: provider={model_config.provider}, model={model_config.name}")
                response = await client.ainvoke(langchain_messages)

                # 构建返回结果
                return LLMResponse(content=response.content)

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
        async with self.redis_gate.acquire(model_config.name, model_config.max_in_flight):
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

            except Exception as e:
                # 记录错误日志
                logger.error(f"LLM 流式调用失败: {str(e)}")
                raise


# 创建全局 LLM 客户端实例
llm_client = LLMClient()
