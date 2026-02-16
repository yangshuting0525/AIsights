"""
Feishu (飞书) Message Sender Configuration
===========================================
发送到飞书的配置文件
"""

# ============================================
# 应用凭证
# ============================================
# APP ID
APP_ID = "cli_a91abb05e7789bcc" # 在这里填写你的APP_ID

# APP Secret
APP_SECRET = "I8m8GLzYnaZsC1dyFMpyofRRyrfIv0BM" # 在这里填写你的APP_SECRET

# ============================================
# 接收者配置
# ============================================
# 接收者ID类型: open_id / union_id / user_id / email / chat_id
RECEIVE_ID_TYPE = "chat_id"

# 群聊ID（当发送给群聊时）
CHAT_ID = "oc_951aab32a7a6f99ab00e3ad5bf277831" # 访问该网址后可得：https://open.feishu.cn/api-explorer/cli_a91abb05e7789bcc?apiName=list&project=im&resource=chat&version=v1

# ============================================
# API 配置
# ============================================
# 获取 tenant_access_token 的地址
TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"

# 发送消息的地址
MESSAGE_URL = "https://open.feishu.cn/open-apis/im/v1/messages"

# ============================================
# 消息配置
# ============================================
# 消息类型: text / post / interactive
MESSAGE_TYPE = "post"

# 发送者名称
SENDER_NAME = "AI News Bot"

# 消息最大长度（超过会分段发送）
MAX_MESSAGE_LENGTH = 15000
