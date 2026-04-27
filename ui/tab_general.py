"""通用设置标签页：主题、数据保留、语言、开机自启、隐私声明、版本信息"""

import tkinter as tk
from tkinter import ttk

from src.version import VERSION
from src.i18n import t, init as init_i18n, get_language

# 主题：(存储 key, 翻译 key)
THEMES = [
    ('minimal',    'theme.minimal'),
    ('fairy_tale', 'theme.fairy_tale'),
    ('business',   'theme.business'),
]
# 数据保留：(存储 key, 翻译 key)
RETENTIONS = [
    ('unlimited', 'retention.unlimited'),
    ('1year',     'retention.1year'),
    ('3months',   'retention.3months'),
    ('1month',    'retention.1month'),
]
LANGUAGES = [('zh-CN', '中文'), ('en', 'English')]


def _translated_values(pairs):
    """返回显示文本列表（兼容翻译 key 和直接文本）"""
    result = []
    for _, val in pairs:
        translated = t(val)
        result.append(translated if translated != val else val)
    return result


def _key_to_display(pairs, key_val):
    """将存储 key 转换为对应的显示文本"""
    for k, val in pairs:
        if k == key_val:
            translated = t(val)
            return translated if translated != val else val
    return key_val


def _display_to_key(pairs, display_val):
    """将显示文本反向映射回存储 key"""
    for k, val in pairs:
        translated = t(val)
        text = translated if translated != val else val
        if text == display_val:
            return k
    return display_val


class TabGeneral(ttk.Frame):
    """通用设置"""

    def __init__(self, parent, config_manager, startup_manager):
        super().__init__(parent)
        self._config = config_manager
        self._startup = startup_manager
        # 测试运行模式检测：exe 在 dist\ 目录或非冻结环境，禁止写入开机自启
        import sys as _sys
        from pathlib import Path as _Path
        if getattr(_sys, 'frozen', False):
            _exe = _Path(_sys.executable)
            self._is_test_run = ('dist' in _exe.parent.parts)
        else:
            self._is_test_run = True
        self._build()

    def _build(self):
        pad = {'padx': 12, 'pady': 6, 'sticky': 'ew'}
        self.columnconfigure(1, weight=1)

        # 初始值：配置或快捷方式实际存在即为 True
        startup_enabled = self._config.auto_start or self._startup.is_startup_enabled()
        self._auto_start_var = tk.BooleanVar(value=startup_enabled)

        row = 0

        # 主题
        ttk.Label(self, text=t('general.theme')).grid(row=row, column=0, **pad)
        self._theme_var = tk.StringVar(value=_key_to_display(THEMES, self._config.theme))
        theme_combo = ttk.Combobox(self, textvariable=self._theme_var,
                                    values=_translated_values(THEMES), state='readonly', width=16)
        theme_combo.grid(row=row, column=1, **pad)
        row += 1

        # 数据保留
        ttk.Label(self, text=t('general.retention')).grid(row=row, column=0, **pad)
        self._retention_var = tk.StringVar(value=_key_to_display(RETENTIONS, self._config.data_retention))
        ret_combo = ttk.Combobox(self, textvariable=self._retention_var,
                                 values=_translated_values(RETENTIONS),
                                 state='readonly', width=16)
        ret_combo.grid(row=row, column=1, **pad)
        row += 1

        # 语言
        ttk.Label(self, text=t('general.language')).grid(row=row, column=0, **pad)
        self._lang_var = tk.StringVar(value=_key_to_display(LANGUAGES, get_language()))
        lang_combo = ttk.Combobox(self, textvariable=self._lang_var,
                                  values=_translated_values(LANGUAGES), state='readonly', width=16)
        lang_combo.grid(row=row, column=1, **pad)
        lang_combo.bind('<<ComboboxSelected>>', self._on_language_change)
        row += 1

        # 开机自启（测试模式下禁用）
        _startup_label = t('general.auto_start')
        if self._is_test_run:
            _startup_label += '  [测试模式不可用]'
        _startup_cb = ttk.Checkbutton(self, text=_startup_label, variable=self._auto_start_var)
        _startup_cb.grid(row=row, column=0, columnspan=2, **pad)
        if self._is_test_run:
            _startup_cb.state(['disabled'])
        row += 1

        # 开机弹昨日报告
        self._auto_report_var = tk.BooleanVar(value=self._config.auto_show_daily_report)
        ttk.Checkbutton(self, text=t('general.auto_show_report'), variable=self._auto_report_var
                        ).grid(row=row, column=0, columnspan=2, **pad)
        row += 1

        ttk.Separator(self, orient='horizontal').grid(row=row, column=0, columnspan=2, sticky='ew', pady=8)
        row += 1

        ttk.Label(self, text=t('general.privacy'), font=('', 10, 'bold')).grid(row=row, column=0, **pad)
        row += 1
        ttk.Label(self, text=t('general.privacy_text'), wraplength=400, justify='left',
                  foreground='#666').grid(row=row, column=0, columnspan=2, **pad)
        row += 1

        ttk.Separator(self, orient='horizontal').grid(row=row, column=0, columnspan=2, sticky='ew', pady=8)
        row += 1
        ttk.Label(self, text=t('general.version', version=VERSION), foreground='#888').grid(row=row, column=0, **pad)

    def _on_language_change(self, event=None):
        new_lang = _display_to_key(LANGUAGES, self._lang_var.get())
        init_i18n(new_lang)

    def apply(self):
        """应用按钮回调：统一提交所有变更"""
        self._config.theme = _display_to_key(THEMES, self._theme_var.get())
        self._config.data_retention = _display_to_key(RETENTIONS, self._retention_var.get())
        self._config.language = _display_to_key(LANGUAGES, self._lang_var.get())
        self._config.auto_start = self._auto_start_var.get()
        self._config.auto_show_daily_report = self._auto_report_var.get()
        self._config.save()
        if self._is_test_run:
            return  # 测试模式：跳过开机自启写入，保护 CLI 环境
        if self._auto_start_var.get():
            self._startup.enable_startup()
        else:
            self._startup.disable_startup()
