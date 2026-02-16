#!/usr/bin/env python3
"""
Feishu Message Sender
=====================
通过飞书机器人发送消息

使用方法:
    python feishu_sender.py --text "测试消息"
    python feishu_sender.py --file summaries/summary_xxx.md
    python feishu_sender.py --latest  # 发送最新总结
    python feishu_sender.py --daily   # 发送今日总结
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import Optional

import requests

from feishu_config import (
    APP_ID,
    APP_SECRET,
    TOKEN_URL,
    MESSAGE_URL,
    RECEIVE_ID_TYPE,
    CHAT_ID,
    MESSAGE_TYPE,
    MAX_MESSAGE_LENGTH,
)


class FeishuSender:
    """飞书消息发送器"""

    def __init__(self):
        self.app_id = APP_ID
        self.app_secret = APP_SECRET
        self.token_url = TOKEN_URL
        self.message_url = MESSAGE_URL
        self.receive_id_type = RECEIVE_ID_TYPE
        self.receive_id = CHAT_ID
        self.message_type = MESSAGE_TYPE

        self.tenant_access_token = None
        self.token_expires = 0

    def get_tenant_access_token(self) -> Optional[str]:
        """获取 tenant_access_token"""
        # 检查token是否过期（提前5分钟刷新）
        if self.tenant_access_token and datetime.now().timestamp() < self.token_expires - 300:
            return self.tenant_access_token

        print("[飞书] 获取 access token...")

        headers = {"Content-Type": "application/json; charset=utf-8"}
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }

        try:
            response = requests.post(self.token_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()

            result = response.json()
            if result.get("code") == 0:
                self.tenant_access_token = result.get("tenant_access_token")
                # token有效期2小时，设定过期时间为1.5小时后
                self.token_expires = datetime.now().timestamp() + 5400
                print("[飞书] Access token 获取成功")
                return self.tenant_access_token
            else:
                print(f"[错误] 获取token失败: {result.get('msg')}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"[错误] 网络请求失败: {e}")
            return None

    def send_text_message(self, text: str) -> bool:
        """发送文本消息"""
        return self._send_message("text", {"text": text})

    def send_rich_text_message(self, title: str, content: str) -> bool:
        """发送副文本消息（支持格式）"""
        # 构建飞书副文本格式
        content_json = {
            "zh_cn": {
                "title": title,
                "content": [
                    [
                        {
                            "tag": "text",
                            "text": content
                        }
                    ]
                ]
            }
        }
        return self._send_message("post", content_json)

    def _send_message(self, msg_type: str, content: dict) -> bool:
        """发送消息（通用方法）"""
        token = self.get_tenant_access_token()
        if not token:
            return False

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }

        params = {"receive_id_type": self.receive_id_type}

        # content 需要序列化为字符串
        payload = {
            "receive_id": self.receive_id,
            "msg_type": msg_type,
            "content": json.dumps(content, ensure_ascii=False)
        }

        try:
            response = requests.post(
                self.message_url,
                params=params,
                headers=headers,
                json=payload,
                timeout=30
            )

            # 打印详细错误信息
            print(f"[调试] HTTP状态码: {response.status_code}")
            print(f"[调试] 响应内容: {response.text[:500]}")

            response.raise_for_status()

            result = response.json()
            if result.get("code") == 0:
                print(f"[成功] 消息已发送")
                return True
            else:
                print(f"[错误] 发送失败: {result.get('msg')}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"[错误] 网络请求失败: {e}")
            return False

    def split_and_send(self, text: str, title: str = "") -> bool:
        """如果消息太长，分段发送"""
        if len(text) <= MAX_MESSAGE_LENGTH:
            return self.send_rich_text_message(title, text)

        # 分段发送
        chunks = []
        current = ""

        # 按行分割
        lines = text.split('\n')
        for line in lines:
            if len(current) + len(line) + 1 > MAX_MESSAGE_LENGTH:
                if current:
                    chunks.append(current)
                current = line
            else:
                current += '\n' + line if current else line

        if current:
            chunks.append(current)

        print(f"[提示] 消息过长，拆分为 {len(chunks)} 段发送")

        success = True
        for i, chunk in enumerate(chunks, 1):
            chunk_title = f"{title} ({i}/{len(chunks)})" if title else f"第 {i}/{len(chunks)} 部分"
            if not self.send_rich_text_message(chunk_title, chunk):
                success = False

        return success

    def send_file_content(self, filepath: str) -> bool:
        """发送文件内容"""
        if not os.path.exists(filepath):
            print(f"[错误] 文件不存在: {filepath}")
            return False

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # 尝试提取标题
        lines = content.split('\n')
        title = "AI News Summary"
        for line in lines:
            if line.startswith('# '):
                title = line[2:].strip()
                break

        # 去掉Markdown标题
        clean_content = content
        if clean_content.startswith('# '):
            clean_content = '\n'.join(lines[1:])

        print(f"[飞书] 发送文件: {filepath}")
        return self.split_and_send(clean_content, title)

    def test_connection(self) -> bool:
        """测试连接"""
        print("\n" + "=" * 50)
        print("[测试] 飞书连接测试")
        print("=" * 50)

        token = self.get_tenant_access_token()
        if token:
            print(f"[成功] Access token 获取成功")
            print(f"[配置] 发送类型: {self.message_type}")
            print(f"[配置] 接收ID: {self.receive_id}")
            return True
        else:
            print("[失败] Access token 获取失败")
            return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='飞书消息发送器'
    )
    parser.add_argument(
        '--text', '-t',
        type=str,
        help='发送文本消息'
    )
    parser.add_argument(
        '--file', '-f',
        type=str,
        help='发送文件内容'
    )
    parser.add_argument(
        '--latest', '-l',
        action='store_true',
        help='发送最新总结 (summaries/latest.md)'
    )

    parser.add_argument(
        '--daily',
        action='store_true',
        help='发送今日总结'
    )
    parser.add_argument(
        '--test', '-T',
        action='store_true',
        help='测试飞书连接'
    )


    args = parser.parse_args()

    # 如果没有任何参数，显示帮助
    if len(sys.argv) == 1:
        parser.print_help()
        print("\n[示例]")
        print("  python feishu_sender.py --test          # 测试连接")
        print("  python feishu_sender.py --text 'hello'  # 发送文本")
        print("  python feishu_sender.py --file xxx.md   # 发送文件")
        print("  python feishu_sender.py --latest        # 发送最新总结")
        return

    sender = FeishuSender()

    # 测试连接
    if args.test:
        sender.test_connection()
        return

    # 发送文本
    if args.text:
        sender.send_text_message(args.text)
        return

    # 发送文件
    if args.file:
        sender.send_file_content(args.file)
        return

    # 发送最新总结
    if args.latest:
        latest_file = "summaries/latest.md"
        if os.path.exists(latest_file):
            sender.send_file_content(latest_file)
        else:
            # 查找最新的summary文件
            summaries_dir = "summaries"
            if os.path.exists(summaries_dir):
                files = [f for f in os.listdir(summaries_dir) if f.endswith('.md')]
                if files:
                    latest = sorted(files)[-1]
                    sender.send_file_content(os.path.join(summaries_dir, latest))
                else:
                    print("[错误] summaries 目录为空")
            else:
                print("[错误] summaries 目录不存在")
        return

if __name__ == '__main__':
    main()
