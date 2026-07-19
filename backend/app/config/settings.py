from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings

# .env 放在 backend/ 目录，与 requirements.txt 同级
_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    """
    只存放环境级别的配置：机密信息 + 部署时才能确定的选项（如模型名）。
    温度、token 上限等行为参数由各 Agent 的 AgentConfig 自行定义。
    """

    # DeepSeek（OpenAI 兼容接口）——慢模型：推理模型，用于最终预测
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-pro"

    # 快模型：非推理、便宜快，用于意图理解/队名抽取等轻任务。
    # fast_api_key/fast_base_url 留空则回退主 DeepSeek（deepseek-chat 同账号即可用）。
    fast_model: str = "deepseek-chat"
    fast_api_key: str = ""
    fast_base_url: str = ""

    # Tavily 网页搜索
    tavily_api_key: str = ""
    tavily_base_url: str = "https://api.tavily.com"

    # football-data（免费，结构化数据主力：教练/战绩/赛程）
    football_data_api_key: str = ""
    football_data_base_url: str = "https://api.football-data.org/v4"

    # api-football（免费层仅开放 2022~2024 赛季，对 2026 无效，未接入预测；
    # 留作将来历史数据 / RAG 层使用，或升级付费后启用）
    api_football_api_key: str = ""
    api_football_base_url: str = "https://v3.football.api-sports.io"

    # The Odds API（赔率，免费 500次/月，覆盖 2026 世界杯）
    the_odds_api_key: str = ""
    the_odds_base_url: str = "https://api.the-odds-api.com"

    # RAG（历史世界杯知识库）
    embedding_model: str = "BAAI/bge-small-zh-v1.5"   # 中文向量模型，512维
    hf_home: str = "D:/code/hf_cache"                 # 模型缓存目录（D盘）
    chroma_path: str = "D:/code/WC-agent/backend/data/chroma"  # 向量库落盘位置
    rag_collection: str = "wc_history"                # Chroma collection 名
    rag_top_k: int = 5                                # 默认召回条数
    rag_min_sim: float = 0.5                          # 相似度阈值，低于则视为不相关丢弃

    # MCP：是否把赔率工具切到 MCP server（odds_server）走协议调用。
    # False=进程内直接调 OddsTool（默认）；True=agent 作为 MCP client 消费。
    # 开关存在的意义：可随时回退、可 A/B 对比，切换不改业务代码。
    use_mcp_odds: bool = False

    # Redis（短期会话记忆，Docker 容器 localhost:6379）
    redis_url: str = "redis://localhost:6379/0"

    # MySQL（长期用户记忆，Docker 容器 localhost:3306）
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = "wcpass"
    mysql_db: str = "wc_agent"

    # 短期会话记忆
    session_max_messages: int = 20     # 滑动窗口保留的消息条数（约 10 轮）
    session_ttl_seconds: int = 604800  # 会话空闲过期时间（7 天）

    # 上下文管理
    model_context_window: int = 65536  # 模型上下文窗口（token 圆环的分母）
    context_token_budget: int = 3000   # 历史窗口 token 预算，超了触发滚动摘要压缩
    context_keep_recent: int = 6       # 压缩时保留最近多少条原文（其余摘要成梗概）

    # 鉴权（JWT）——上线前务必在 .env 里覆盖 jwt_secret 为随机长串
    jwt_secret: str = "dev-only-change-me-in-env"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 10080    # 令牌有效期（7 天）

    # 图形验证码：答案存 Redis 的过期时间
    captcha_ttl_seconds: int = 300     # 5 分钟内有效

    # 未来扩展其他提供商时在这里添加
    # anthropic_api_key: str = ""
    # serpapi_api_key: str = ""

    # 日志
    log_dir: str = "D:/code/logs"   # 日志文件目录，放 D 盘
    log_level: str = "INFO"         # 控制台/文件最低级别；调试时可设 DEBUG
    log_to_file: bool = True        # 是否写文件（开发时可关掉只看控制台）

    class Config:
        env_file = str(_ENV_FILE)
        env_file_encoding = "utf-8"


settings = Settings()
