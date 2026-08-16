"""
配置模块

业务说明：
管理环境变量；业务上游 URL 不由本配置默认提供，须经租户 A Token 在控制台配置。
门禁转发 OpenClaw 使用内部 Gateway URL/secret；管理员种子用于控制台。
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """封装环境变量配置。"""

    model_config = SettingsConfigDict(
        env_file="env/.env.local",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    server_port: int = 8000
    log_level: str = "INFO"

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    glm_api_key: str = ""
    glm_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    siliconflow_api_key: str = ""
    siliconflow_base_url: str = "https://api.siliconflow.cn/v1"
    modelscope_api_key: str = ""
    modelscope_base_url: str = "https://api-inference.modelscope.cn/v1"

    # --- Agent 控制面 / 门禁（与 Go 同址 MySQL）---
    # 例：mysql+pymysql 不用 URL 库时拆字段
    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_database: str = "pangbao_agent"
    # 控制台会话签名密钥
    console_secret_key: str = "change-me-console-secret"
    # 管理员种子（首次启动写入/校验）
    agent_admin_username: str = "admin"
    agent_admin_password: str = "admin-change-me"
    # 门禁转发 OpenClaw（内部单 token；多 G 在 DB）
    internal_gateway_url: str = "http://127.0.0.1:18789"
    internal_gateway_token: str = ""
    # 飞轮：空=进程内
    flywheel_base_url: str = ""

    redis_url: str = "redis://localhost:6379/0"
    chroma_persist_dir: str = "data/chroma_db"
    embedding_model: str = "BAAI/bge-small-zh-v1.5"

    companion_session_ttl_days: int = 7
    companion_session_max_turns: int = 3

    qa_fast_path_enabled: bool = True
    qa_sim_threshold: float = 0.8
    qa_quality_min: float = 0.7
    rewrite_timeout_s: float = 5.0

    clear_feeding_intents_on_startup: bool = False


settings = Settings()
