"""通用设置标签页：主题、数据保留、语言、开机自启、隐私声明、版本信息"""

import tkinter as tk
from tkinter import ttk

from src.version import VERSION
from src.i18n import t, init as init_i18n, get_language

THEMES = [
    ('minimal', 'minimal'),
    ('fairy_tale', 'fairy_tale'),
    ('business', 'business'),
]
LANGUAGES = [('zh-CN', '中文'), ('en', 'English')]


class TabGeneral(ttk.Frame):
    """通用设置"""

    def __init__(self, parent, config_manager, startup_manager):
        super().__init__(parent)
        self._config = config_manager
        self._startup = startup_manager
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
        self._theme_var = tk.StringVar(value=self._config.theme)
        theme_combo = ttk.Combobox(self, textvariable=self._theme_var,
                                    values=[v for _, v in THEMES], state='readonly', width=16)
        theme_combo.grid(row=row, column=1, **pad)
        row += 1

        # 数据保留
        ttk.Label(self, text=t('general.retention')).grid(row=row, column=0, **pad)
        self._retention_var = tk.StringVar(value=self._config.data_retention)
        ret_combo = ttk.Combobox(self, textvariable=self._retention_var,
                                 values=['unlimited', '1year', '3months', '1month'],
                                 state='readonly', width=16)
        ret_combo.grid(row=row, column=1, **pad)
        row += 1

        # 语言
        ttk.Label(self, text=t('general.language')).grid(row=row, column=0, **pad)
        self._lang_var = tk.StringVar(value=get_language())
        lang_combo = ttk.Combobox(self, textvariable=self._lang_var,
                                  values=[v for _, v in LANGUAGES], state='readonly', width=16)
        lang_combo.grid(row=row, column=1, **pad)
        lang_combo.bind('<<ComboboxSelected>>', self._on_language_change)
        row += 1

        # 开机自启
        ttk.Checkbutton(self, text=t('general.auto_start'), variable=self._auto_start_var
                        ).grid(row=row, column=0, columnspan=2, **pad)
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
        new_lang = self._lang_var.get()
        init_i18n(new_lang)

    def apply(self):
        """应用按钮回调：统一提交所有变更"""
        self._config.theme = self._theme_var.get()
        self._config.data_retention = self._retention_var.get()
        self._config.language = self._lang_var.get()
        self._config.auto_start = self._auto_start_var.get()
        self._config.auto_show_daily_report = self._auto_report_var.get()
        self._config.save()
        if self._auto_start_var.get():
            self._startup.enable_startup()
        else:
            self._startup.disable_startup()
