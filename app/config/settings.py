"""
配置模块

业务说明：
本模块负责管理所有环境变量配置，使用 pydantic-settings 进行类型安全的配置管理。
配置项包括服务端口、LLM API Key、兄弟仓服务地址、Redis 地址等。

设计思路：
1. 使用 pydantic-settings 的 BaseSettings 自动读取环境变量
2. 支持通过 .env 文件加载配置（开发环境）
3. 生产环境通过 Docker Compose 环境变量注入
4. 提供默认值，便于本地开发调试
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    配置类

    业务说明：
    封装所有环境变量配置，提供类型安全的访问方式。
    """

    # 模型配置：指定配置文件路径
    model_config = SettingsConfigDict(
        env_file=".env",  # 开发环境从 .env 文件加载
        env_file_encoding="utf-8",
        extra="ignore",  # 忽略未定义的环境变量
    )

    # 服务配置
    server_port: int = 8000  # 服务端口
    log_level: str = "WARNING"  # 日志级别

    # LLM 配置 - DeepSeek
    deepseek_api_key: str = ""  # DeepSeek API Key
    deepseek_base_url: str = "https://api.deepseek.com/v1"  # DeepSeek API 地址

    # LLM 配置 - Zhipu (GLM)
    glm_api_key: str = ""  # Zhipu API Key
    glm_base_url: str = "https://open.bigmodel.cn/api/paas/v4"  # Zhipu API 地址

    # 兄弟仓服务地址
    history_service_url: str = "http://localhost:9801"  # 历史服务地址
    device_service_url: str = "http://localhost:9803"  # 设备服务地址

    # Redis 配置
    redis_url: str = "redis://localhost:6379/0"  # Redis 连接地址

    # 向量数据库配置
    chroma_persist_dir: str = "data/chroma_db"  # Chroma 数据持久化目录
    embedding_model: str = "BAAI/bge-small-zh-v1.5"  # Embedding 模型名称

    # 缓存配置
    event_cache_ttl_hours: int = 24  # 事件字典缓存 TTL（小时）


# 创建全局配置实例
settings = Settings()