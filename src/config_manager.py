"""
配置管理器
- 存储路径：%APPDATA%/UsageTracker/config.json（卸载不丢失）
- 原子写入（先写临时文件再 os.replace）
- schema 校验，非法值回退默认值
- 版本号迁移
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

from .constants import (
    CONFIG_PATH, DEFAULT_CHECK_INTERVAL, DEFAULT_DATA_RETENTION,
    DEFAULT_THEME, DEFAULT_AUTO_START,
)
from .version import VERSION

logger = logging.getLogger(__name__)

DEFAULT_CONFIG: dict[str, Any] = {
    'version': VERSION,
    'theme': DEFAULT_THEME,
    'data_retention': DEFAULT_DATA_RETENTION,
    'check_interval': DEFAULT_CHECK_INTERVAL,
    'auto_start': DEFAULT_AUTO_START,
    'auto_show_daily_report': True,
    'language': 'zh-CN',
    'privacy_accepted': False,
    'browsers': [],
    'game_dirs': [],
    'ignored_apps': [],
    'custom_categories': [],
}

# 合法取值
_VALID_THEMES = {'minimal', 'fairy_tale', 'business'}
_VALID_RETENTIONS = {'unlimited', '1year', '3months', '1month'}
_VALID_LANGUAGES = {'zh-CN', 'en'}


class ConfigManager:
    """配置读写管理"""

    def __init__(self, config_path: str | Path | None = None):
        self.config_path = Path(config_path) if config_path else CONFIG_PATH
        self._config: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """加载配置文件，不存在则用默认值"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                self._config = self._validate(saved)
                logger.info('配置已加载: %s', self.config_path)
            except Exception as e:
                logger.warning('配置加载失败，使用默认值: %s', e)
                self._config = dict(DEFAULT_CONFIG)
        else:
            self._config = dict(DEFAULT_CONFIG)
            self.save()

    def _validate(self, raw: dict[str, Any]) -> dict[str, Any]:
        """校验并修正配置值"""
        cfg = dict(DEFAULT_CONFIG)
        for key, default in DEFAULT_CONFIG.items():
            if key in raw:
                val = raw[key]
                if key == 'theme' and val not in _VALID_THEMES:
                    val = default
                elif key == 'data_retention' and val not in _VALID_RETENTIONS:
                    val = default
                elif key == 'check_interval' and not isinstance(val, int | float):
                    val = default
                elif key == 'language' and val not in _VALID_LANGUAGES:
                    val = default
                cfg[key] = val
        for key in raw:
            if key not in cfg:
                cfg[key] = raw[key]
        return cfg

    def save(self) -> None:
        """原子写入配置文件"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.config_path.with_suffix('.tmp')
        try:
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.config_path)
        except Exception as e:
            logger.error('配置保存失败: %s', e)
            if tmp.exists():
                tmp.unlink()

    # ---- 便捷属性 ----

    @property
    def theme(self) -> str:
        return self._config.get('theme', DEFAULT_THEME)

    @theme.setter
    def theme(self, value: str) -> None:
        if value in _VALID_THEMES:
            self._config['theme'] = value

    @property
    def data_retention(self) -> str:
        return self._config.get('data_retention', DEFAULT_DATA_RETENTION)

    @data_retention.setter
    def data_retention(self, value: str) -> None:
        if value in _VALID_RETENTIONS:
            self._config['data_retention'] = value

    @property
    def check_interval(self) -> int:
        return self._config.get('check_interval', DEFAULT_CHECK_INTERVAL)

    @property
    def auto_start(self) -> bool:
        return self._config.get('auto_start', DEFAULT_AUTO_START)

    @auto_start.setter
    def auto_start(self, value: bool) -> None:
        self._config['auto_start'] = bool(value)

    @property
    def auto_show_daily_report(self) -> bool:
        return self._config.get('auto_show_daily_report', True)

    @auto_show_daily_report.setter
    def auto_show_daily_report(self, value: bool) -> None:
        self._config['auto_show_daily_report'] = bool(value)

    @property
    def language(self) -> str:
        return self._config.get('language', 'zh-CN')

    @language.setter
    def language(self, value: str) -> None:
        if value in _VALID_LANGUAGES:
            self._config['language'] = value

    @property
    def privacy_accepted(self) -> bool:
        return self._config.get('privacy_accepted', False)

    @privacy_accepted.setter
    def privacy_accepted(self, value: bool) -> None:
        self._config['privacy_accepted'] = bool(value)

    @property
    def browsers(self) -> list[str]:
        return self._config.get('browsers', [])

    @property
    def game_dirs(self) -> list[str]:
        return self._config.get('game_dirs', [])

    @property
    def ignored_apps(self) -> list[dict[str, str]]:
        return self._config.get('ignored_apps', [])

    @property
    def custom_categories(self) -> list[dict[str, Any]]:
        return self._config.get('custom_categories', [])

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._config[key] = value

    # ---- 忽略名单 ----

    def add_ignored_app(self, exe_path: str, app_name: str) -> bool:
        for item in self._config['ignored_apps']:
            if item.get('exe_path') == exe_path:
                return False
        import datetime
        self._config['ignored_apps'].append({
            'exe_path': exe_path,
            'app_name': app_name,
            'ignored_at': datetime.datetime.now().isoformat(),
        })
        self.save()
        return True

    def remove_ignored_app(self, exe_path: str) -> bool:
        before = len(self._config['ignored_apps'])
        self._config['ignored_apps'] = [
            item for item in self._config['ignored_apps']
            if item.get('exe_path') != exe_path
        ]
        if len(self._config['ignored_apps']) < before:
            self.save()
            return True
        return False

    def is_ignored(self, exe_path: str) -> bool:
        return any(
            item.get('exe_path') == exe_path
            for item in self._config['ignored_apps']
        )

    # ---- 自定义分类 ----

    def add_custom_category(self, category_id: str, name: str,
                            color: str = '#0078D4') -> bool:
        for cat in self._config['custom_categories']:
            if cat.get('id') == category_id or cat.get('name') == name:
                return False
        self._config['custom_categories'].append({
            'id': category_id, 'name': name, 'color': color, 'apps': [],
        })
        self.save()
        return True

    def remove_custom_category(self, category_id: str) -> bool:
        before = len(self._config['custom_categories'])
        self._config['custom_categories'] = [
            cat for cat in self._config['custom_categories']
            if cat.get('id') != category_id
        ]
        if len(self._config['custom_categories']) < before:
            self.save()
            return True
        return False

    def add_app_to_category(self, category_id: str, exe_path: str) -> bool:
        """向自定义分类添加应用程序"""
        for cat in self._config['custom_categories']:
            if cat.get('id') == category_id:
                apps = cat.setdefault('apps', [])
                if exe_path.lower() not in [a.lower() for a in apps]:
                    apps.append(exe_path)
                    self.save()
                    return True
                return False
        return False

    def remove_app_from_category(self, category_id: str, exe_path: str) -> bool:
        """从自定义分类移除应用程序"""
        for cat in self._config['custom_categories']:
            if cat.get('id') == category_id:
                apps = cat.setdefault('apps', [])
                before = len(apps)
                cat['apps'] = [a for a in apps if a.lower() != exe_path.lower()]
                if len(cat['apps']) < before:
                    self.save()
                    return True
                return False
        return False

    def get_custom_category_for_exe(self, exe_path: str) -> dict | None:
        for cat in self._config['custom_categories']:
            apps = cat.get('apps', [])
            if exe_path.lower() in [a.lower() for a in apps]:
                return cat
        return None
