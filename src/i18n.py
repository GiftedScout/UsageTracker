"""轻量国际化模块 — JSON 翻译文件 + 运行时切换"""

import json
import locale
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_LOCALE_DIR = Path(__file__).parent.parent / 'locales'
_current_lang = 'zh-CN'
_translations: dict[str, str] = {}


def _detect_system_language() -> str:
    """根据系统语言自动检测"""
    try:
        lang, _ = locale.getdefaultlocale()
        if lang and lang.lower().startswith('zh'):
            return 'zh-CN'
    except Exception:
        pass
    return 'en'


def init(language: str | None = None) -> None:
    """加载指定语言的翻译文件，None 时自动检测系统语言"""
    global _current_lang, _translations
    if not language:
        language = _detect_system_language()
    _current_lang = language
    locale_file = _LOCALE_DIR / f'{language}.json'
    if locale_file.exists():
        with open(locale_file, 'r', encoding='utf-8') as f:
            _translations = json.load(f)
        logger.info('已加载翻译: %s', locale_file)
    else:
        logger.warning('翻译文件不存在: %s，使用 key 原文', locale_file)
        _translations = {}


def t(key: str, **kwargs) -> str:
    """翻译函数：根据 key 获取翻译文本，支持 format 占位符"""
    text = _translations.get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text


def get_language() -> str:
    return _current_lang
