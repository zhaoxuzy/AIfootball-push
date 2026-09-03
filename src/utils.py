import os
import json
import time
import random
import hashlib
import base64
import hmac
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from src.config import DINGTALK_WEBHOOK, DINGTALK_SECRET

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/118.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
]

# 增强的请求头模板（用于绕过SofaScore 403）
DEFAULT_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Origin": "https://www.sofascore.com",
    "Referer": "https://www.sofascore.com/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
}

def fetch_url(url: str, retry: int = 3, timeout: int = 20, headers: Optional[Dict] = None) -> Optional[str]:
    """
    通用HTTP GET请求，带重试和完整请求头
    增加超时时间到20秒，解决ClubElo超时问题
    """
    for attempt in range(retry):
        try:
            if headers is None:
                headers = DEFAULT_HEADERS.copy()
                headers["User-Agent"] = random.choice(USER_AGENTS)
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp.text
        except requests.exceptions.Timeout as e:
            print(f"请求超时 (尝试 {attempt+1}/{retry}): {url} -> {e}")
            if attempt < retry - 1:
                time.sleep(random.uniform(3, 6))
        except requests.exceptions.HTTPError as e:
            print(f"HTTP错误 (尝试 {attempt+1}/{retry}): {url} -> {e}")
            if attempt < retry - 1:
                time.sleep(random.uniform(3, 6))
        except Exception as e:
            print(f"请求失败 (尝试 {attempt+1}/{retry}): {url} -> {e}")
            if attempt < retry - 1:
                time.sleep(random.uniform(2, 5))
    return None

def fetch_json(url: str, retry: int = 3, timeout: int = 20, headers: Optional[Dict] = None) -> Optional[Dict]:
    """请求JSON数据"""
    text = fetch_url(url, retry, timeout, headers)
    if text:
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {url} -> {e}")
            return None
    return None

def now_str() -> str:
    """返回当前UTC+8时间字符串"""
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")

def save_json(data: Any, filename: str, output_dir: str = "output") -> str:
    """保存JSON文件到output目录，返回文件路径"""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    filepath = Path(output_dir) / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return str(filepath)

def send_dingtalk(title: str, content: str, webhook: Optional[str] = None, secret: Optional[str] = None) -> bool:
    """发送钉钉消息（支持加签）"""
    webhook = webhook or DINGTALK_WEBHOOK
    secret = secret or DINGTALK_SECRET
    if not webhook:
        print("钉钉webhook未配置，跳过推送")
        return False

    if secret:
        timestamp = str(round(time.time() * 1000))
        sign_str = timestamp + "\n" + secret
        signature = base64.b64encode(
            hmac.new(secret.encode('utf-8'), sign_str.encode('utf-8'), digestmod=hashlib.sha256).digest()
        ).decode('utf-8')
        webhook = f"{webhook}&timestamp={timestamp}&sign={signature}"

    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": content
        }
    }
    try:
        resp = requests.post(webhook, json=payload, timeout=10)
        if resp.status_code == 200:
            result = resp.json()
            if result.get('errcode') == 0:
                print("钉钉推送成功")
                return True
            else:
                print(f"钉钉推送失败: {result}")
        else:
            print(f"钉钉推送HTTP错误: {resp.status_code}")
    except Exception as e:
        print(f"钉钉推送异常: {e}")
    return False
