"""
自动更新检测
启动时检查 GitHub Releases 最新版本，发现新版本时通知用户。
"""

import json
import logging
import os
import threading
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com/repos/GiftedScout/UsageTracker/releases/latest"
REPO_URL = "https://github.com/GiftedScout/UsageTracker/releases"

# 缓存路径（避免每次启动都拉 API）
_CACHE_PATH = Path(os.path.expandvars('%TEMP%')) / 'UsageTracker_update_cache.json'
_CACHE_TTL = 3600  # 1 小时


def _compare_versions(v1: str, v2: str) -> int:
    """比较两个版本号。返回: 1(v1>v2), 0(相等), -1(v1<v2)"""
    parts1 = [int(x) for x in v1.split('.')]
    parts2 = [int(x) for x in v2.split('.')]
    for i in range(max(len(parts1), len(parts2))):
        a = parts1[i] if i < len(parts1) else 0
        b = parts2[i] if i < len(parts2) else 0
        if a > b:
            return 1
        elif a < b:
            return -1
    return 0


def check_update(current_version: str, force: bool = False) -> dict | None:
    """检查是否有新版本。返回版本信息或 None。
    
    force=True 时忽略缓存，总是请求 API。
    """
    # 1. 读缓存
    if not force and _CACHE_PATH.exists():
        try:
            age = os.path.getmtime(_CACHE_PATH)
            import time
            if time.time() - age < _CACHE_TTL:
                with open(_CACHE_PATH, 'r') as f:
                    cached = json.load(f)
                if cached.get('version') and cached['version'] > current_version:
                    return cached
                elif cached.get('version') and _compare_versions(
                        cached['version'], current_version) <= 0:
                    return None  # 缓存确认已是最新
        except Exception:
            pass

    # 2. 请求 GitHub API
    try:
        req = urlopen(GITHUB_API, timeout=10)
        data = json.loads(req.read().decode('utf-8'))
        latest_tag = data.get("tag_name", "").lstrip("v")
        if not latest_tag:
            return None

        # 写缓存
        info = None
        if _compare_versions(latest_tag, current_version) > 0:
            info = {
                "version": latest_tag,
                "url": data.get("html_url", REPO_URL),
                "notes": data.get("body", ""),
                "name": data.get("name", f"v{latest_tag}"),
            }

        try:
            _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(_CACHE_PATH, 'w') as f:
                json.dump(info or {"version": current_version}, f)
        except Exception:
            pass

        return info
    except URLError as e:
        logger.debug('检查更新失败（网络问题）: %s', e)
        return None
    except json.JSONDecodeError as e:
        logger.debug('检查更新失败（响应解析）: %s', e)
        return None
    except Exception as e:
        logger.debug('检查更新异常: %s', e)
        return None


def check_update_async(current_version: str,
                       callback=None, force: bool = False) -> None:
    """异步执行版本检查，callback(new_version_info_or_None) 在主线程调用。
    
    如果 callback 为 None，结果会被忽略（只用于缓存预热）。
    """
    def _run():
        try:
            result = check_update(current_version, force=force)
            if callback:
                callback(result)
        except Exception as e:
            logger.error('异步检查更新失败: %s', e)
    
    t = threading.Thread(target=_run, daemon=True, name='update-check')
    t.start()
