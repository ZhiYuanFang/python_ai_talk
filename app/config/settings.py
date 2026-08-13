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
        env_file="env/.env.local",  # 本地开发环境文件加载
        env_file_encoding="utf-8",
        extra="ignore",  # 忽略未定义的环境变量
    )

    # 服务配置
    server_port: int = 8000  # 服务端口
    log_level: str = "INFO"  # 日志级别

    # LLM 配置 - DeepSeek（付费通道；默认不进免费保底列表）
    deepseek_api_key: str = ""  # DeepSeek API Key
    deepseek_base_url: str = "https://api.deepseek.com/v1"  # DeepSeek API 地址

    # LLM 配置 - Zhipu (GLM，Flash 等永久免费档常作 Go 首选)
    glm_api_key: str = ""  # Zhipu API Key
    glm_base_url: str = "https://open.bigmodel.cn/api/paas/v4"  # Zhipu API 地址

    # LLM 配置 - 硅基流动（国内永久免费模型，$0 + 限速）
    siliconflow_api_key: str = ""
    siliconflow_base_url: str = "https://api.siliconflow.cn/v1"

    # LLM 配置 - 魔搭 ModelScope（国内，每日免费推理次数重置）
    modelscope_api_key: str = ""
    modelscope_base_url: str = "https://api-inference.modelscope.cn/v1"

    # 免费保底链（仅 llm_client.invoke；stream 不使用）
    # 逗号分隔 provider:model（model 可含 /）；未传 model 时整表即候选序
    # 含智谱 Flash，便于仅靠 env 调整免费顺序；不含付费 deepseek
    llm_fallback_models: str = (
        "glm:glm-4.7-flash,"
        "siliconflow:Qwen/Qwen3.5-4B,"
        "siliconflow:Qwen/Qwen2.5-7B-Instruct,"
        "modelscope:Qwen/Qwen3-8B"
    )

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

    # 陪伴会话（tip/clinic 共享）：按 device_no，近 N 轮，TTL 天（滑动续期）
    companion_session_ttl_days: int = 7
    companion_session_max_turns: int = 3  # 进 prompt / Redis 截断一致，默认 3 轮省 token

    # 护理留意飞轮：suggestionId → 建议快照映射 TTL（天）
    care_alert_flywheel_ttl_days: int = 7
    # 全局 prompt / ledger 目录（Docker 挂载卷；本地默认相对项目 data/）
    care_alert_prompt_dir: str = "data/care_alert"
    # 对比样例块硬顶字符数（防 prompt 无限增长）
    care_alert_examples_max_chars: int = 1200
    # 每累计多少条新反馈触发一次样例重写
    care_alert_flywheel_rewrite_every: int = 20
    # 距上次重写最少间隔（秒）；与条数阈值任一满足即可重写
    care_alert_flywheel_rewrite_min_interval_s: int = 3600
    # 对比样例槽位最低证据条数（单侧）
    care_alert_flywheel_min_evidence: int = 2
    # ledger 滚动保留最近行数
    care_alert_ledger_max_lines: int = 500

    # 知识注入预算：检索后按 score 过滤，默认 K=1 且 score>=0.6，否则不注入
    knowledge_min_score: float = 0.6
    knowledge_prompt_top_k: int = 1
    # 通识知识 quality_score 硬过滤下限（缺省元数据按 store 默认 0.8）
    knowledge_quality_min: float = 0.7

    # Q&A 捷径：改写超时、相似度/质量阈值、总开关
    qa_fast_path_enabled: bool = True
    qa_sim_threshold: float = 0.8
    qa_quality_min: float = 0.7
    rewrite_timeout_s: float = 5.0

    # 启动一次性清空意图缓存 feeding_intents（默认关；清完务必改回 false）
    clear_feeding_intents_on_startup: bool = False


# 创建全局配置实例
settings = Settings()