"""通用设置标签页：主题、数据保留、开机自启、隐私声明、版本信息"""

import tkinter as tk
from tkinter import ttk
import logging

from src.version import VERSION, APP_NAME

logger = logging.getLogger(__name__)

THEMES = [('简约', 'minimal'), ('童话', 'fairy_tale'), ('商务', 'business')]
RETENTIONS = [('不限制', 'unlimited'), ('1年', '1year'), ('3个月', '3months'), ('1个月', '1month')]


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

        row = 0
        ttk.Label(self, text='主题风格:').grid(row=row, column=0, **pad)
        self._theme_var = tk.StringVar(value=self._config.theme)
        for i, (label, val) in enumerate(THEMES):
            if val == self._config.theme:
                self._theme_var.set(val)
        theme_combo = ttk.Combobox(self, textvariable=self._theme_var,
                                    values=[v for _, v in THEMES], state='readonly', width=16)
        theme_combo.grid(row=row, column=1, **pad)
        theme_combo.bind('<<ComboboxSelected>>', lambda e: self._save_theme())
        row += 1

        ttk.Label(self, text='数据保留:').grid(row=row, column=0, **pad)
        self._retention_var = tk.StringVar(value=self._config.data_retention)
        ret_combo = ttk.Combobox(self, textvariable=self._retention_var,
                                 values=[v for _, v in RETENTIONS], state='readonly', width=16)
        ret_combo.grid(row=row, column=1, **pad)
        ret_combo.bind('<<ComboboxSelected>>', lambda e: self._save_retention())
        row += 1

        self._auto_start_var = tk.BooleanVar(value=self._config.auto_start)
        ttk.Checkbutton(self, text='开机自动启动', variable=self._auto_start_var,
                        command=self._toggle_auto_start).grid(row=row, column=0, columnspan=2, **pad)
        row += 1

        ttk.Separator(self, orient='horizontal').grid(row=row, column=0, columnspan=2, sticky='ew', pady=8)
        row += 1

        ttk.Label(self, text='隐私声明', font=('', 10, 'bold')).grid(row=row, column=0, **pad)
        row += 1
        privacy_text = '所有数据仅存储在本地设备，不会联网上传。\n数据库和配置文件位于系统 AppData 目录。'
        ttk.Label(self, text=privacy_text, wraplength=400, justify='left',
                  foreground='#666').grid(row=row, column=0, columnspan=2, **pad)
        row += 1

        ttk.Separator(self, orient='horizontal').grid(row=row, column=0, columnspan=2, sticky='ew', pady=8)
        row += 1
        ttk.Label(self, text=f'版本: {VERSION}', foreground='#888').grid(row=row, column=0, **pad)

    def _save_theme(self):
        self._config.theme = self._theme_var.get()
        self._config.save()

    def _save_retention(self):
        self._config.data_retention = self._retention_var.get()
        self._config.save()

    def _toggle_auto_start(self):
        self._config.auto_start = self._auto_start_var.get()
        self._config.save()
        if self._auto_start_var.get():
            self._startup.enable_startup()
        else:
            self._startup.disable_startup()

    def apply(self):
        """应用按钮回调"""
        self._save_theme()
        self._save_retention()
        self._toggle_auto_start()
