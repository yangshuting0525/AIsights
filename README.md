# AI 热点自动监控

自动监控 Twitter 上 AI 领域博主的推文，使用 AI 总结后推送到飞书。

## 配置

### 1. config.py - Twitter 监控配置

```python
TWITTER_API_KEY = "你的API密钥"  # 从 twitterapi.io 获取
WATCHED_ACCOUNTS = ["OpenAI", "AnthropicAI", ...]  # 要监控的账号
MONITOR_INTERVAL_SECONDS = 3600  # 监控间隔（秒）
```

### 2. summarizer_config.py - AI 总结配置

```python
API_BASE_URL = "https://api.openai.com/v1"  # OpenAI 兼容接口
API_KEY = "你的API密钥"
MODEL = "gpt-4o-mini"  # 模型名称
```

### 3. feishu_config.py - 飞书推送配置（可选）

```python
APP_ID = "你的应用ID"
APP_SECRET = "你的应用Secret"
CHAT_ID = "群聊ID"
```

## 运行

```bash
# 安装依赖
pip install -r requirements.txt

# 1、抓取一次推文
python twitter_monitor.py --once

# 持续抓取推文
python twitter_monitor.py

# 2、AI 总结
python summarizer.py

# 3、推送到飞书
python feishu_sender.py --latest
```


## 流程

**步骤 0：配置阶段**
↓ 编辑 config.py                             
↓ 编辑 summarizer_config.py                  
↓ 编辑 feishu_config.py   



**步骤 1：数据收集** 
run: python twitter_monitor.py --once   
twitter_monitor.py                           
   ↓ 调用 Twitter API                         
   ↓ 使用 data_manager.py 保存               
   ↓ 生成文件：                                
      - data/tweets_latest.json   (最新)     
      - data/tweets_daily_*.json  (每日)     
      - data/tweets_all.json      (全部)   

              

**步骤 2：AI 总结**  
run: python summarizer.py                                                         
summarizer.py                                
   ↓ 读取 tweets_*.json                       
   ↓ 调用 AI API                              
   ↓ 生成文件：                                
      - summaries/summary_*.md  

              

**步骤 3：推送飞书（可选）** 
run: python feishu_sender.py --latest       
feishu_sender.py                             
   ↓ 读取 summaries/summary_*.md             
   ↓ 调用飞书 API                             
   ↓ 发送到群聊                                

