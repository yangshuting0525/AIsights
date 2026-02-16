"""
Twitter AI News Monitor - Configuration
========================================
抓取推文的配置文件
"""

# ============================================
# API 配置
# ============================================
TWITTER_API_KEY = "new1_419760df9da043bebe6e4fcdda76e3e2"  # 在这里填入你的API密钥

API_BASE_URL = "https://api.twitterapi.io"

# ============================================
# 关注的AI领域博主 (Twitter用户名，不包含@)
# ============================================
WATCHED_ACCOUNTS = [
    # 示例格式: "elonmusk", "AndrewNG", "ylecun"
    # 请在此处添加你关注的博主用户名

    # 著名AI/ML研究者
    # "AndrewNG",      # Andrew Ng (AI教育)
    # "ylecun",        # Yann LeCun (Meta AI)
    # "JeffDean",      # Jeff Dean (Google AI)
    # "goodfellow_ian", # Ian Goodfellow (GAN发明者)

    # AI公司/实验室
    # "OpenAI",
    # "GoogleDeepMind",
    # "AnthropicAI",
    # " StabilityAI",

    # AI领域意见领袖
    # "karpathy",      # Andrej Karpathy
    # "sama",          # Sam Altman
    # "drfeigenberg",  # Daniel Feinberg

    # 在这里添加你关注的博主：
    "Alibaba_Qwen",
    "AndrewNG",
    "arena",
    "MiniMax__AI",
    "KwaiAICoder",
    "Zai_org",
    "lmstudio",
    "deepseek_ai",
    "OpenRouterAI",
    "AnthropicAI",
    "OpenAI",
    "huggingface",
    "Kimi_Moonshot",
    "Ali_TongyiLab",
    "cline",
    "OpenAIDevs",
    "cerebras",
    "Baidu_Inc",
    "ManusAI",
    "vista8",
    "karminski3",
    "op7418",
    "geekbb",
]

# ============================================
# 监控频率设置
# ============================================
# 监控间隔时间（秒）
# 建议值：
#   300      = 5分钟（频繁监控，可能消耗较多API额度）
#   600      = 10分钟
#   1800     = 30分钟
#   3600     = 1小时（推荐）
#   7200     = 2小时
#   14400    = 4小时
#   21600    = 6小时
#   43200    = 12小时
#   86400    = 24小时

MONITOR_INTERVAL_SECONDS = 14400

# ============================================
# 保存模式设置 (可以同时启用多个)
# ============================================
# ENABLE_INCREMENTAL: 启用增量模式，所有推文累积到同一个文件
ENABLE_INCREMENTAL = True

# ENABLE_DAILY: 启用每日模式，每天一个增量文件（按天分隔）
ENABLE_DAILY = True

# ENABLE_LATEST: 启用最新模式，每次运行保存这一轮抓到的内容
ENABLE_LATEST = True

# 数据保存目录
DATA_DIR = "data"

# 增量模式文件
INCREMENTAL_FILE = "tweets_all.json"
INCREMENTAL_IDS_FILE = "tweets_ids.json"

# 每日模式文件前缀
DAILY_PREFIX = "tweets_daily"

# 最新模式文件
LATEST_FILE = "tweets_latest.json"
