"""
全局常量
"""

import os
import sys
from pathlib import Path

from .version import VERSION, APP_NAME

# ---- 数据路径 ----
# 所有数据统一放在安装目录下（打包模式）或项目根目录（开发模式）
if getattr(sys, 'frozen', False):
    # PyInstaller 打包后：exe 所在目录
    _BASE_DIR = Path(sys.executable).resolve().parent
else:
    # 开发模式：项目根目录
    _BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = _BASE_DIR / 'data'
CONFIG_DIR = _BASE_DIR / 'config'
REPORT_DIR = _BASE_DIR / 'reports'
LOG_DIR = _BASE_DIR / 'logs'
CRASH_LOG_DIR = _BASE_DIR / 'logs'
BRIDGE_DIR = _BASE_DIR / 'bridge'
FEEDBACK_DIR = _BASE_DIR / 'feedback'
STEAM_CACHE_PATH = _BASE_DIR / 'data' / 'steam_games.json'
INSTALL_DIR = _BASE_DIR

DB_PATH = DATA_DIR / 'usage_data.db'
CONFIG_PATH = CONFIG_DIR / 'config.json'

# ---- 分类常量 ----
CATEGORY_BROWSER = 'browser'
CATEGORY_GAME = 'game'
CATEGORY_OTHER = 'other'

CATEGORY_NAMES = {
    CATEGORY_BROWSER: '浏览器',
    CATEGORY_GAME: '游戏',
    CATEGORY_OTHER: '其他',
}

# ---- 默认值 ----
DEFAULT_CHECK_INTERVAL = 5
DEFAULT_DATA_RETENTION = 'unlimited'  # unlimited | 1year | 3months | 1month
DEFAULT_THEME = 'fairy_tale'  # minimal | fairy_tale | business
DEFAULT_AUTO_START = True
BRIDGE_POLL_INTERVAL = 30  # 秒
TOOLTIP_UPDATE_INTERVAL = 30  # 秒
AUTO_SAVE_INTERVAL = 300  # 秒（5分钟）
MIN_SESSION_DURATION = 5  # 秒，忽略短会话
MIN_AUTO_SAVE_DURATION = 10  # 秒，自动保存最小增量（原 60s，过大会丢失轻度使用数据）


def migrate_from_legacy():
    """从旧版路径（%LOCALAPPDATA%/UsageTracker 和 %APPDATA%/UsageTracker）迁移数据到新路径"""
    import shutil
    import logging
    _log = logging.getLogger('constants')

    old_data_dir = Path(os.environ.get('LOCALAPPDATA', '')) / APP_NAME
    old_config_dir = Path(os.environ.get('APPDATA', '')) / APP_NAME

    if not old_data_dir.exists() and not old_config_dir.exists():
        return

    if _BASE_DIR == old_data_dir or _BASE_DIR == old_config_dir:
        return  # 已经在新路径

    _log.info('检测到旧版数据目录，开始迁移...')

    # 迁移数据库
    old_db = old_data_dir / 'usage_data.db'
    if old_db.exists() and not DB_PATH.exists():
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(old_db, DB_PATH)
            _log.info('数据库已迁移: %s -> %s', old_db, DB_PATH)
        except Exception as e:
            _log.warning('数据库迁移失败: %s', e)

    # 迁移配置
    old_cfg = old_config_dir / 'config.json'
    if old_cfg.exists() and not CONFIG_PATH.exists():
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(old_cfg, CONFIG_PATH)
            _log.info('配置已迁移: %s -> %s', old_cfg, CONFIG_PATH)
        except Exception as e:
            _log.warning('配置迁移失败: %s', e)

    # 迁移报告
    old_reports = old_data_dir / 'reports'
    if old_reports.exists():
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        for f in old_reports.glob('*.html'):
            dst = REPORT_DIR / f.name
            if not dst.exists():
                try:
                    shutil.copy2(f, dst)
                except Exception:
                    pass

    # 迁移其他小文件
    for old_name, new_path in [
        ('steam_games.json', STEAM_CACHE_PATH),
    ]:
        old_f = old_data_dir / old_name
        if old_f.exists() and not new_path.exists():
            new_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(old_f, new_path)
            except Exception:
                pass

    _log.info('数据迁移完成')
