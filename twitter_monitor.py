#!/usr/bin/env python3
"""
Twitter AI News Monitor (高级搜索版)
=====================================
寻找推文
使用高级搜索API, 一次请求获取多个用户的推文, 更节省API次数


使用方法:
    python twitter_monitor.py              # 持续监控模式
    python twitter_monitor.py --once       # 只运行一次
    python twitter_monitor.py --export     # 导出已收集的推文
    python twitter_monitor.py --stats      # 查看统计数据
"""

import requests
import time
import signal
import sys
import argparse
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional

from config import (
    TWITTER_API_KEY,
    WATCHED_ACCOUNTS,
    MONITOR_INTERVAL_SECONDS,
    API_BASE_URL,
    DATA_DIR,
    ENABLE_INCREMENTAL,
    ENABLE_DAILY,
    ENABLE_LATEST,
    INCREMENTAL_FILE,
    INCREMENTAL_IDS_FILE,
    DAILY_PREFIX,
    LATEST_FILE,
)
from data_manager import DataManager


class TwitterMonitor:
    """Twitter监控器(使用高级搜索)"""

    def __init__(self):
        self.api_key = TWITTER_API_KEY
        self.base_url = API_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            'X-API-Key': self.api_key,
            'Accept': 'application/json'
        })
        self.data_manager = DataManager(
            data_dir=DATA_DIR,
            incremental_file=INCREMENTAL_FILE,
            incremental_ids_file=INCREMENTAL_IDS_FILE,
            daily_prefix=DAILY_PREFIX,
            latest_file=LATEST_FILE,
            enable_incremental=ENABLE_INCREMENTAL,
            enable_daily=ENABLE_DAILY,
            enable_latest=ENABLE_LATEST,
        )
        self.running = True
        self.last_fetch_time = None  # 上次获取的时间

        # 注册信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """处理退出信号"""
        print("\n[系统] 收到退出信号，正在停止监控...")
        self.running = False

    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """发起API请求"""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[错误] API请求失败: {e}")
            return None

    def _build_search_query(self, accounts: List[str]) -> str:
        """构建高级搜索查询语法"""
        # 组合多个用户: from:user1 OR from:user2 OR from:user3
        user_query = " OR ".join([f"from:{account.strip()}" for account in accounts if account.strip()])
        return user_query

    def _format_timestamp(self, dt: datetime) -> str:
        """格式化时间戳为Twitter搜索格式"""
        # 格式: YYYY-MM-DD_HH:MM:SS_UTC
        return dt.strftime("%Y-%m-%d_%H:%M:%S_UTC")

    def get_tweets_advanced_search(self, accounts: List[str], since_hours: float = 1.0) -> List[Dict]:
        """
        使用高级搜索获取多个用户的推文

        Args:
            accounts: 用户名列表
            since_hours: 获取过去多少小时的推文

        Returns:
            推文列表
        """
        if not accounts:
            return []

        all_tweets = []
        cursor = ""

        # 构建查询: 从指定用户中搜索
        query = self._build_search_query(accounts)
        print(f"  [搜索] 查询: {query[:60]}...")

        # 计算起始时间
        since_time = datetime.now(timezone.utc) - timedelta(hours=since_hours)
        since_param = self._format_timestamp(since_time)
        full_query = f"{query} since:{since_param}"

        print(f"  [搜索] 时间范围: {since_hours}小时内")

        while True:
            params = {
                'query': full_query,
                'queryType': 'Latest',
                'cursor': cursor if cursor else '',
            }

            result = self._make_request('twitter/tweet/advanced_search', params)

            if result is None:
                break

            tweets = result.get('tweets', [])
            all_tweets.extend(tweets)

            has_next = result.get('has_next_page', False)
            cursor = result.get('next_cursor', '')

            if not has_next or not cursor:
                break

            # 避免请求过快
            time.sleep(0.5)

        # 去重并按时间排序
        seen_ids = set()
        unique_tweets = []
        for tweet in all_tweets:
            tweet_id = tweet.get('id')
            if tweet_id and tweet_id not in seen_ids:
                seen_ids.add(tweet_id)
                unique_tweets.append(tweet)

        # 按时间排序（新的在前）
        unique_tweets.sort(key=lambda x: x.get('createdAt', ''), reverse=True)

        return unique_tweets

    def run_once(self) -> None:
        """运行一次监控"""
        print(f"\n{'='*60}")
        print(f"[监控] 开始获取推文 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"[模式] 增量:{ENABLE_INCREMENTAL} | 每日:{ENABLE_DAILY} | 最新:{ENABLE_LATEST}")
        print(f"[用户] {len(WATCHED_ACCOUNTS)} 个")
        print(f"{'='*60}")

        # 计算搜索时间范围
        search_hours = MONITOR_INTERVAL_SECONDS / 3600.0

        # 一次性获取所有用户的推文（节省API调用）
        print(f"\n[API] 使用高级搜索，一次性获取所有用户的推文...")
        tweets = self.get_tweets_advanced_search(WATCHED_ACCOUNTS, search_hours)

        if tweets:
            print(f"\n[完成] 共获取 {len(tweets)} 条推文")
        else:
            print(f"\n[完成] 没有获取到推文")

        # 保存到所有启用的模式
        result = self.data_manager.save_tweets(tweets)

        # 打印统计
        print(f"\n[统计]")
        if ENABLE_INCREMENTAL:
            print(f"  增量模式: 累计 {self.data_manager.get_tweets_count()} 条推文")
        if ENABLE_DAILY:
            print(f"  每日模式: 本次新增 {result['daily_new']} 条")
        if ENABLE_LATEST:
            print(f"  最新模式: 本次 {result['latest_count']} 条")

        # 更新最后获取时间
        self.last_fetch_time = datetime.now(timezone.utc)

    def run_continuous(self) -> None:
        """持续监控模式"""
        print(f"\n{'='*60}")
        print(f"[启动] Twitter AI 监控器已启动")
        print(f"[配置] 监控 {len(WATCHED_ACCOUNTS)} 个账号")
        print(f"[配置] 监控间隔: {MONITOR_INTERVAL_SECONDS} 秒 ({MONITOR_INTERVAL_SECONDS/3600:.1f} 小时)")
        print(f"[模式] 增量:{ENABLE_INCREMENTAL} | 每日:{ENABLE_DAILY} | 最新:{ENABLE_LATEST}")
        print(f"[API] 使用高级搜索，每次只获取新增推文")
        print(f"[提示] 按 Ctrl+C 停止")
        print(f"{'='*60}\n")

        while self.running:
            self.run_once()
            if self.running:
                print(f"\n[等待] 等待 {MONITOR_INTERVAL_SECONDS} 秒后进行下一次监控...")
                time.sleep(MONITOR_INTERVAL_SECONDS)

        print("\n[停止] 监控器已停止")

    def export_data(self) -> None:
        """导出数据"""
        if ENABLE_INCREMENTAL:
            count = self.data_manager.get_tweets_count()
            print(f"\n[导出] 增量模式当前存储 {count} 条推文")
            output_file = self.data_manager.export_to_markdown()
            print(f"[完成] 导出完成: {output_file}")
        else:
            print("[导出] 增量模式未启用，无法导出")

    def show_stats(self) -> None:
        """显示统计信息"""
        stats = self.data_manager.get_stats()

        print(f"\n[统计]")
        print(f"  增量模式: {'启用' if stats['incremental']['enabled'] else '禁用'}")
        if stats['incremental']['enabled']:
            print(f"    总推文数: {stats['incremental']['total_tweets']}")
            print(f"    唯一ID数: {stats['incremental']['unique_ids']}")
            file_size = stats['incremental'].get('file_size', 0)
            print(f"    文件大小: {file_size:.1f} KB")

        print(f"  每日模式: {'启用' if stats['daily']['enabled'] else '禁用'}")
        if stats['daily']['enabled']:
            print(f"    每日文件数: {stats['daily'].get('count', 0)}")
            files = stats['daily'].get('files', [])
            if files:
                print(f"    最新文件: {files[0]}")

        print(f"  最新模式: {'启用' if stats['latest']['enabled'] else '禁用'}")

    def list_daily_files(self) -> None:
        """列出每日文件"""
        files = self.data_manager.list_daily_files()
        print(f"\n[每日文件] 共 {len(files)} 个:")
        for i, f in enumerate(files[:20]):
            print(f"  {i+1}. {f}")
        if len(files) > 20:
            print(f"  ... 还有 {len(files) - 20} 个")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='Twitter AI News Monitor - 使用高级搜索API'
    )
    parser.add_argument(
        '--once', '-o',
        action='store_true',
        help='只运行一次，不持续监控'
    )
    parser.add_argument(
        '--export', '-e',
        action='store_true',
        help='导出已收集的推文为Markdown格式'
    )
    parser.add_argument(
        '--stats', '-s',
        action='store_true',
        help='显示当前数据统计'
    )
    parser.add_argument(
        '--daily',
        action='store_true',
        help='列出所有每日文件'
    )

    args = parser.parse_args()

    # 检查API密钥
    if TWITTER_API_KEY == "YOUR_API_KEY_HERE":
        print("[错误] 请先在 config.py 中设置你的 API 密钥!")
        print("编辑 config.py 文件，将 TWITTER_API_KEY 替换为你的实际API密钥")
        sys.exit(1)

    # 检查账号配置
    if not WATCHED_ACCOUNTS or all(not a.strip() for a in WATCHED_ACCOUNTS):
        print("[错误] 请在 config.py 中配置要监控的Twitter账号!")
        sys.exit(1)

    # 检查是否至少启用了一种模式
    if not any([ENABLE_INCREMENTAL, ENABLE_DAILY, ENABLE_LATEST]):
        print("[错误] 请在 config.py 中至少启用一种保存模式!")
        sys.exit(1)

    monitor = TwitterMonitor()

    if args.export:
        monitor.export_data()
        return

    if args.stats:
        monitor.show_stats()
        return

    if args.daily:
        monitor.list_daily_files()
        return

    if args.once:
        monitor.run_once()
    else:
        monitor.run_continuous()


if __name__ == '__main__':
    main()
