#!/usr/bin/env python3
"""
Twitter AI News Summarizer
===========================
读取推文数据(twitter_monitor.py), 调用AI进行总结

使用方法:
    python summarizer.py              # 运行总结
    python summarizer.py --latest     # 只总结最新数据
    python summarizer.py --daily      # 总结今日数据
    python summarizer.py --all        # 总结所有历史数据
"""

import os
import json
import re
import argparse
from datetime import datetime
from typing import List, Dict, Optional

import requests

from summarizer_config import (
    API_BASE_URL,
    API_KEY,
    MODEL,
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
    DATA_SOURCE,
    DATA_DIR,
    OUTPUT_DIR,
    PRINT_RESULT,
    MAX_TWEETS,
)


class TweetSummarizer:
    """推文总结器"""

    def __init__(self):
        self.api_base_url = API_BASE_URL.rstrip('/')
        self.api_key = API_KEY
        self.model = MODEL
        self.system_prompt = SYSTEM_PROMPT
        self.user_template = USER_PROMPT_TEMPLATE
        self.data_dir = DATA_DIR
        self.output_dir = OUTPUT_DIR
        self.max_tweets = MAX_TWEETS

        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)

    def _load_latest_tweets(self) -> List[Dict]:
        """加载最新模式的推文"""
        filepath = os.path.join(self.data_dir, "tweets_latest.json")
        if not os.path.exists(filepath):
            print(f"[警告] 文件不存在: {filepath}")
            return []
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('tweets', [])

    def _load_daily_tweets(self) -> List[Dict]:
        """加载今日的推文"""
        today = datetime.now().strftime("%Y%m%d")
        prefix = "tweets_daily"
        filename = f"{prefix}_{today}.json"
        filepath = os.path.join(self.data_dir, filename)

        if not os.path.exists(filepath):
            print(f"[警告] 今日文件不存在: {filepath}")
            return []
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('tweets', [])

    def _load_all_tweets(self) -> List[Dict]:
        """加载所有历史推文"""
        filepath = os.path.join(self.data_dir, "tweets_all.json")
        if not os.path.exists(filepath):
            print(f"[警告] 文件不存在: {filepath}")
            return []
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('tweets', [])

    def load_tweets(self, source: str = None) -> List[Dict]:
        """加载推文数据"""
        source = source or DATA_SOURCE

        print(f"[数据] 加载 {source} 数据...")

        if source == "latest":
            tweets = self._load_latest_tweets()
        elif source == "daily":
            tweets = self._load_daily_tweets()
        elif source == "all":
            tweets = self._load_all_tweets()
        else:
            print(f"[错误] 未知的数据源: {source}")
            return []

        print(f"[数据] 加载到 {len(tweets)} 条推文")
        return tweets

    def format_tweets_for_ai(self, tweets: List[Dict]) -> str:
        """将推文格式化为AI可读的文本"""
        formatted = []
        for i, tweet in enumerate(tweets[:self.max_tweets], 1):
            author = tweet.get('author', {})
            username = author.get('userName', 'unknown')
            name = author.get('name', 'Unknown')
            text = tweet.get('text', '')
            url = tweet.get('url', '')
            created = tweet.get('createdAt', '')

            formatted.append(f"【{i}】@{username} ({name})")
            formatted.append(f"    内容: {text}")
            formatted.append(f"    链接: {url}")
            formatted.append(f"    时间: {created}")
            formatted.append("")

        return "\n".join(formatted)

    def call_ai_api(self, tweets_text: str, tweets_count: int) -> Optional[str]:
        """调用AI API进行总结"""
        if self.api_key == "YOUR_API_KEY_HERE":
            print("[错误] 请先在 summarizer_config.py 中填写 API_KEY!")
            return None

        url = f"{self.api_base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        user_prompt = self.user_template.format(
            count=tweets_count,
            tweets=tweets_text
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 4096
        }

        print(f"[AI] 正在调用 {self.model} ...")

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=120)
            response.raise_for_status()

            result = response.json()
            message = result['choices'][0]['message']

            # 有些模型会返回 reasoning_content（思维链），只取最终的 content
            summary = message.get('content', '')

            # 如果 content 为空但有 reasoning_content，取后者
            if not summary and message.get('reasoning_content'):
                summary = message.get('reasoning_content', '')
                print("[提示] 模型返回的是思维链内容，非最终结果")

            # 过滤掉 think 标签内容（如 <thinker_block>...</thinker_block>）
            import re
            # 匹配各种 think 标签格式
            think_patterns = [
                r'<thinker_block>.*?</thinker_block>',
                r'<think>.*?</think>',
                r'<thinking>.*?</thinking>',
                r'\[THINKING\].*?\[/THINKING\]',
            ]
            for pattern in think_patterns:
                summary = re.sub(pattern, '', summary, flags=re.DOTALL | re.IGNORECASE)

            # 清理多余的空行
            summary = re.sub(r'\n{3,}', '\n\n', summary)
            summary = summary.strip()

            return summary

        except requests.exceptions.RequestException as e:
            print(f"[错误] API调用失败: {e}")
            return None

    def save_summary(self, summary: str, source: str) -> str:
        """保存总结到文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"summary_{source}_{timestamp}.md"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# AI News Summary\n\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"数据来源: {source}\n\n")
            f.write("---\n\n")
            f.write(summary)

        print(f"[保存] 总结已保存到: {filepath}")
        return filepath

    def run(self, source: str = None) -> Optional[str]:
        """运行总结流程"""
        print(f"\n{'='*60}")
        print(f"[开始] AI推文总结器")
        print(f"{'='*60}")

        # 1. 加载推文
        tweets = self.load_tweets(source)
        if not tweets:
            print("[警告] 没有推文数据可供总结")
            return None

        # 2. 格式化推文
        tweets_text = self.format_tweets_for_ai(tweets)

        # 3. 调用AI
        summary = self.call_ai_api(tweets_text, len(tweets))
        if not summary:
            return None

        # 4. 打印结果
        if PRINT_RESULT:
            print(f"\n{'='*60}")
            print("[总结结果]")
            print(f"{'='*60}")
            print(summary)

        # 5. 保存结果
        source = source or DATA_SOURCE
        filepath = self.save_summary(summary, source)

        print(f"\n[完成] 总结完成!")
        return filepath


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='AI推文总结器 - 调用AI总结推文内容'
    )
    parser.add_argument(
        '--latest', '-l',
        action='store_true',
        help='只总结最新数据 (tweets_latest.json)'
    )
    parser.add_argument(
        '--daily', '-d',
        action='store_true',
        help='总结今日数据'
    )
    parser.add_argument(
        '--all', '-a',
        action='store_true',
        help='总结所有历史数据'
    )

    args = parser.parse_args()

    # 确定数据源
    if args.latest:
        source = "latest"
    elif args.daily:
        source = "daily"
    elif args.all:
        source = "all"
    else:
        source = None  # 使用配置文件中的默认值

    summarizer = TweetSummarizer()
    summarizer.run(source)


if __name__ == '__main__':
    main()
