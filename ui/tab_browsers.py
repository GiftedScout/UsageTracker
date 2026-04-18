"""浏览器管理标签页：显示已识别浏览器 + 手动添加/移除"""

import tkinter as tk
from tkinter import ttk
import logging

logger = logging.getLogger(__name__)

DEFAULT_BROWSERS = {
    'msedge.exe', 'chrome.exe', 'firefox.exe',
    'brave.exe', 'opera.exe', 'vivaldi.exe', 'arc.exe',
}


class TabBrowsers(ttk.Frame):
    """浏览器管理"""

    def __init__(self, parent, config_manager, app_classifier):
        super().__init__(parent)
        self._config = config_manager
        self._classifier = app_classifier
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)

        ttk.Label(self, text='已识别的浏览器', font=('', 9, 'bold')).grid(
            row=0, column=0, sticky='w', padx=12, pady=(8, 4))

        self._count_label = ttk.Label(self, text='')
        self._count_label.grid(row=1, column=0, sticky='w', padx=24, pady=2)

        self._listbox = tk.Listbox(self, height=10)
        self._listbox.grid(row=2, column=0, sticky='nsew', padx=12, pady=4)
        self.rowconfigure(2, weight=1)

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=3, column=0, sticky='ew', padx=12, pady=4)

        ttk.Label(btn_frame, text='进程名:').pack(side='left')
        self._add_var = tk.StringVar()
        ttk.Entry(btn_frame, textvariable=self._add_var, width=20).pack(side='left', padx=4)
        ttk.Button(btn_frame, text='添加', command=self._add_browser).pack(side='left')
        ttk.Button(btn_frame, text='移除选中', command=self._remove_browser).pack(side='left', padx=4)

        self._populate()

    def _populate(self):
        self._listbox.delete(0, 'end')
        installed = self._classifier.installed_browsers
        custom = set()
        if self._config:
            custom = {b.lower() for b in self._config.browsers}
        # 全部浏览器：默认 + 自定义
        all_browsers = DEFAULT_BROWSERS | custom
        for exe in sorted(all_browsers):
            if exe in custom and exe not in DEFAULT_BROWSERS:
                tag = ' [自定义]'
            elif exe not in installed:
                tag = ' [未检测到]'
            else:
                tag = ''
            self._listbox.insert('end', f'{exe}{tag}')
        det = len(installed & DEFAULT_BROWSERS)
        cus = len(custom)
        self._count_label.config(
            text=f'已检测 {det} 个  |  自定义 {cus} 个')

    def _add_browser(self):
        name = self._add_var.get().strip().lower()
        if not name or not name.endswith('.exe'):
            return
        if name in self._classifier.browsers:
            return
        browsers = list(self._config.browsers)
        browsers.append(name)
        self._config.set('browsers', browsers)
        self._config.save()
        self._add_var.set('')
        self._populate()

    def _remove_browser(self):
        sel = self._listbox.curselection()
        if not sel:
            return
        text = self._listbox.get(sel[0])
        exe_name = text.split(' ')[0].lower()
        if exe_name in DEFAULT_BROWSERS:
            return
        browsers = [b for b in self._config.browsers if b.lower() != exe_name]
        self._config.set('browsers', browsers)
        self._config.save()
        self._populate()

    def apply(self):
        pass
