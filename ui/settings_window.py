"""设置主窗口：7 标签页 Notebook + 确定/取消/应用"""

import tkinter as tk
from tkinter import ttk
import logging

from .tab_general import TabGeneral
from .tab_categories import TabCategories
from .tab_browsers import TabBrowsers
from .tab_games import TabGames
from .tab_ignore import TabIgnore
from .tab_database import TabDatabase
from .tab_feedback import TabFeedback

logger = logging.getLogger(__name__)


class SettingsWindow:
    """设置窗口管理器（非 Frame，独立 Toplevel）"""

    def __init__(self, parent, config_manager, startup_manager,
                 app_classifier, data_store, crash_handler=None):
        self._config = config_manager
        self._startup = startup_manager
        self._classifier = app_classifier
        self._data_store = data_store
        self._crash_handler = crash_handler

        self._window = tk.Toplevel(parent) if parent else tk.Tk()
        self._window.title('UsageTracker 设置')
        self._window.geometry('700x500')
        self._window.resizable(True, True)
        self._window.protocol('WM_DELETE_WINDOW', self._on_cancel)

        # 如果是独立窗口（parent 为 None），居中
        if not parent:
            self._window.withdraw()
            self._update_idletasks()
            w = 700
            h = 500
            x = (self._window.winfo_screenwidth() - w) // 2
            y = (self._window.winfo_screenheight() - h) // 2
            self._window.geometry(f'{w}x{h}+{x}+{y}')
            self._window.deiconify()

        self._tabs = []
        self._build()
        self._window.grab_set()

    def _build(self):
        nb = ttk.Notebook(self._window)
        nb.pack(fill='both', expand=True, padx=8, pady=(8, 0))

        tabs_data = [
            ('通用设置', TabGeneral),
            ('分类管理', TabCategories),
            ('浏览器管理', TabBrowsers),
            ('游戏目录', TabGames),
            ('忽略名单', TabIgnore),
            ('数据库管理', TabDatabase),
            ('运行日志与反馈', TabFeedback),
        ]

        for label, cls in tabs_data:
            frame = cls(nb, **self._get_tab_kwargs(cls))
            nb.add(frame, text=label)
            self._tabs.append(frame)

        # 底部按钮
        btn_frame = ttk.Frame(self._window)
        btn_frame.pack(fill='x', padx=8, pady=8)
        btn_frame.columnconfigure(0, weight=1)

        ttk.Button(btn_frame, text='确定', width=8,
                   command=self._on_ok).grid(row=0, column=1, padx=4)
        ttk.Button(btn_frame, text='取消', width=8,
                   command=self._on_cancel).grid(row=0, column=2, padx=4)
        ttk.Button(btn_frame, text='应用', width=8,
                   command=self._on_apply).grid(row=0, column=3, padx=4)

    def _get_tab_kwargs(self, cls):
        """根据标签页类返回构造参数"""
        from .tab_general import TabGeneral
        from .tab_categories import TabCategories
        from .tab_browsers import TabBrowsers
        from .tab_games import TabGames
        from .tab_ignore import TabIgnore
        from .tab_database import TabDatabase
        from .tab_feedback import TabFeedback

        if cls is TabGeneral:
            return {'config_manager': self._config, 'startup_manager': self._startup}
        elif cls is TabCategories:
            return {'config_manager': self._config, 'app_classifier': self._classifier}
        elif cls is TabBrowsers:
            return {'config_manager': self._config, 'app_classifier': self._classifier}
        elif cls is TabGames:
            return {'app_classifier': self._classifier, 'config_manager': self._config}
        elif cls is TabIgnore:
            return {'config_manager': self._config, 'data_store': self._data_store}
        elif cls is TabDatabase:
            return {'config_manager': self._config, 'data_store': self._data_store}
        elif cls is TabFeedback:
            return {'crash_handler': self._crash_handler}
        return {}

    def _apply_all(self):
        for tab in self._tabs:
            if hasattr(tab, 'apply'):
                tab.apply()

    def _on_ok(self):
        self._apply_all()
        self._window.destroy()

    def _on_cancel(self):
        self._window.destroy()

    def _on_apply(self):
        self._apply_all()
        self._window.update_idletasks()

    def show(self):
        """显示设置窗口（非阻塞，需 mainloop 在别处运行）"""
        self._window.focus_force()
        return self._window

    def wait(self):
        """等待设置窗口关闭"""
        self._window.wait_window()
