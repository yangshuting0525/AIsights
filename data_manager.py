"""
Twitter AI News Monitor - Data Manager
=======================================
支持三种保存模式（可同时启用）：
1. 增量模式 (incremental): 所有推文累积到同一个文件，自动去重
2. 每日模式 (daily): 每天一个增量文件（按天分隔）
3. 最新模式 (latest): 每次运行保存这一轮抓到的内容
"""

import json
import os
from datetime import datetime
from typing import List, Set, Dict, Any


class DataManager:
    """管理推文数据的存储"""

    def __init__(self, data_dir: str = "data",
                 incremental_file: str = "tweets_all.json",
                 incremental_ids_file: str = "tweets_ids.json",
                 daily_prefix: str = "tweets_daily",
                 latest_file: str = "tweets_latest.json",
                 enable_incremental: bool = True,
                 enable_daily: bool = True,
                 enable_latest: bool = True):

        self.data_dir = data_dir
        self.incremental_file = incremental_file
        self.incremental_ids_file = incremental_ids_file
        self.daily_prefix = daily_prefix
        self.latest_file = latest_file

        self.enable_incremental = enable_incremental
        self.enable_daily = enable_daily
        self.enable_latest = enable_latest

        # 增量模式数据
        self.tweets: List[Dict] = []
        self.seen_tweet_ids: Set[str] = set()

        # 确保数据目录存在
        os.makedirs(data_dir, exist_ok=True)

        # 加载增量模式数据
        if self.enable_incremental:
            self._load_incremental()

    # ========== 增量模式 ==========

    def _load_incremental(self) -> None:
        """加载增量模式的推文"""
        filepath = os.path.join(self.data_dir, self.incremental_file)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.tweets = data
                    else:
                        self.tweets = data.get('tweets', [])
            except (json.JSONDecodeError, IOError) as e:
                print(f"[警告] 加载增量数据失败: {e}")
                self.tweets = []

        # 加载已见ID
        ids_filepath = os.path.join(self.data_dir, self.incremental_ids_file)
        if os.path.exists(ids_filepath):
            try:
                with open(ids_filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.seen_tweet_ids = set(data.get('ids', []))
            except (json.JSONDecodeError, IOError):
                self.seen_tweet_ids = set()

    def _save_incremental(self) -> None:
        """保存增量模式的推文"""
        filepath = os.path.join(self.data_dir, self.incremental_file)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    'tweets': self.tweets,
                    'last_update': datetime.now().isoformat(),
                    'total_count': len(self.tweets)
                }, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"[警告] 保存增量数据失败: {e}")

    def _save_incremental_ids(self) -> None:
        """保存已见推文ID"""
        filepath = os.path.join(self.data_dir, self.incremental_ids_file)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({'ids': list(self.seen_tweet_ids)}, f, ensure_ascii=False)
        except IOError as e:
            print(f"[警告] 保存ID记录失败: {e}")

    # ========== 每日模式 ==========

    def _get_daily_filename(self) -> str:
        """获取今日的每日文件名"""
        today = datetime.now().strftime("%Y%m%d")
        return f"{self.daily_prefix}_{today}.json"

    def _load_daily_tweets(self) -> List[Dict]:
        """加载今日的推文"""
        filename = self._get_daily_filename()
        filepath = os.path.join(self.data_dir, filename)

        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('tweets', [])
            except (json.JSONDecodeError, IOError):
                return []
        return []

    def _save_daily_tweets(self, tweets: List[Dict]) -> None:
        """保存今日的推文"""
        filename = self._get_daily_filename()
        filepath = os.path.join(self.data_dir, filename)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    'date': datetime.now().strftime("%Y-%m-%d"),
                    'tweets': tweets,
                    'count': len(tweets)
                }, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"[警告] 保存每日数据失败: {e}")

    # ========== 最新模式 ==========

    def _save_latest(self, tweets: List[Dict]) -> None:
        """保存最新一轮的推文（覆盖写入）"""
        filepath = os.path.join(self.data_dir, self.latest_file)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    'fetch_time': datetime.now().isoformat(),
                    'tweets': tweets,
                    'count': len(tweets)
                }, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"[警告] 保存最新数据失败: {e}")

    # ========== 主保存方法 ==========

    def save_tweets(self, new_tweets: List[Dict]) -> Dict[str, int]:
        """
        保存推文到所有启用的模式
        返回各模式的保存统计
        """
        result = {
            'incremental_new': 0,
            'daily_new': 0,
            'latest_count': 0,
        }

        # 1. 增量模式
        if self.enable_incremental:
            incremental_new = self._save_incremental_mode(new_tweets)
            result['incremental_new'] = incremental_new

        # 2. 每日模式
        if self.enable_daily:
            daily_count = self._save_daily_mode(new_tweets)
            result['daily_new'] = daily_count

        # 3. 最新模式（直接覆盖，不去重）
        if self.enable_latest:
            self._save_latest(new_tweets)
            result['latest_count'] = len(new_tweets)
            print(f"  [数据] 最新模式: 保存 {len(new_tweets)} 条推文")

        return result

    def _save_incremental_mode(self, new_tweets: List[Dict]) -> int:
        """增量模式：只保存新推文，自动去重"""
        actually_new = []
        for tweet in new_tweets:
            tweet_id = tweet.get('id')
            if tweet_id and tweet_id not in self.seen_tweet_ids:
                actually_new.append(tweet)
                self.seen_tweet_ids.add(tweet_id)

        if actually_new:
            self.tweets = actually_new + self.tweets
            self._save_incremental()
            self._save_incremental_ids()
            print(f"  [数据] 增量模式: 新增 {len(actually_new)} 条推文")

        return len(actually_new)

    def _save_daily_mode(self, new_tweets: List[Dict]) -> int:
        """每日模式：保存今日所有推文，按天分隔"""
        # 加载今日已有的推文
        daily_tweets = self._load_daily_tweets()

        # 获取已有的ID
        existing_ids = {t.get('id') for t in daily_tweets if t.get('id')}

        # 只添加新推文
        actually_new = []
        for tweet in new_tweets:
            tweet_id = tweet.get('id')
            if tweet_id and tweet_id not in existing_ids:
                daily_tweets.append(tweet)
                actually_new.append(tweet_id)
                existing_ids.add(tweet_id)

        if actually_new:
            # 按时间排序（新的在前）
            daily_tweets.sort(key=lambda x: x.get('createdAt', ''), reverse=True)
            self._save_daily_tweets(daily_tweets)
            print(f"  [数据] 每日模式: 今日新增 {len(actually_new)} 条推文")

        return len(actually_new)

    # ========== 辅助方法 ==========

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            'incremental': {
                'enabled': self.enable_incremental,
                'total_tweets': len(self.tweets),
                'unique_ids': len(self.seen_tweet_ids),
            },
            'daily': {
                'enabled': self.enable_daily,
            },
            'latest': {
                'enabled': self.enable_latest,
            }
        }

        # 增量文件大小
        if self.enable_incremental:
            filepath = os.path.join(self.data_dir, self.incremental_file)
            if os.path.exists(filepath):
                stats['incremental']['file_size'] = os.path.getsize(filepath) / 1024

        # 每日文件列表
        if self.enable_daily:
            daily_files = []
            if os.path.exists(self.data_dir):
                for f in os.listdir(self.data_dir):
                    if f.startswith(self.daily_prefix) and f.endswith('.json'):
                        daily_files.append(f)
            stats['daily']['files'] = sorted(daily_files, reverse=True)
            stats['daily']['count'] = len(daily_files)

        return stats

    def list_daily_files(self) -> List[str]:
        """列出所有每日快照文件"""
        files = []
        if os.path.exists(self.data_dir):
            for f in os.listdir(self.data_dir):
                if f.startswith(self.daily_prefix) and f.endswith('.json'):
                    files.append(f)
        return sorted(files, reverse=True)

    def get_all_tweets(self) -> List[Dict]:
        """获取增量模式的所有推文"""
        return self.tweets

    def get_tweets_count(self) -> int:
        """获取增量模式的推文数"""
        return len(self.tweets)

    def export_to_markdown(self, output_file: str = None) -> str:
        """导出为Markdown格式"""
        tweets_to_export = self.tweets

        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"tweets_export_{timestamp}.md"

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# AI News Monitor - Twitter Highlights\n\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"总推文数: {len(tweets_to_export)}\n\n")
            f.write("---\n\n")

            for tweet in tweets_to_export:
                author_name = tweet.get('author', {}).get('name', 'Unknown')
                author_username = tweet.get('author', {}).get('userName', '')
                text = tweet.get('text', '')
                url = tweet.get('url', '')
                created_at = tweet.get('createdAt', '')

                f.write(f"### @{author_username} ({author_name})\n\n")
                f.write(f"{text}\n\n")
                f.write(f"- [查看原推文]({url})\n")
                f.write(f"- 发布时间: {created_at}\n")
                f.write("\n---\n\n")

        print(f"[导出] 已导出到 {output_file}")
        return output_file

    def clear_all_data(self) -> None:
        """清空所有数据"""
        self.tweets = []
        self.seen_tweet_ids = set()

        # 清空增量文件
        for f in [self.incremental_file, self.incremental_ids_file]:
            filepath = os.path.join(self.data_dir, f)
            if os.path.exists(filepath):
                os.remove(filepath)

        # 清空每日文件
        for f in self.list_daily_files():
            os.remove(os.path.join(self.data_dir, f))

        # 清空最新文件
        latest_path = os.path.join(self.data_dir, self.latest_file)
        if os.path.exists(latest_path):
            os.remove(latest_path)

        print("[数据] 已清空所有数据")
