"""忽略名单标签页：管理被忽略的应用"""

import tkinter as tk
from tkinter import ttk
import logging

from src.i18n import t
from ui.process_picker import ProcessPicker

logger = logging.getLogger(__name__)


class TabIgnore(ttk.Frame):
    """忽略名单管理"""

    def __init__(self, parent, config_manager, data_store):
        super().__init__(parent)
        self._config = config_manager
        self._data_store = data_store
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)

        ttk.Label(self, text=t('ignore.ignored_apps'), font=('', 9, 'bold')).grid(
            row=0, column=0, sticky='w', padx=12, pady=(8, 4))

        self._count_label = ttk.Label(self, text='')
        self._count_label.grid(row=1, column=0, sticky='w', padx=24, pady=2)

        # Treeview
        cols = ('app_name', 'exe_path', 'ignored_at')
        self._tree = ttk.Treeview(self, columns=cols, show='headings', height=10)
        self._tree.heading('app_name', text=t('ignore.app_name'))
        self._tree.heading('exe_path', text=t('ignore.exe_path'))
        self._tree.heading('ignored_at', text=t('ignore.ignored_at'))
        self._tree.column('app_name', width=140)
        self._tree.column('exe_path', width=300)
        self._tree.column('ignored_at', width=140)
        self._tree.grid(row=2, column=0, sticky='nsew', padx=12, pady=4)
        self.rowconfigure(2, weight=1)

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=3, column=0, sticky='ew', padx=12, pady=4)
        ttk.Button(btn_frame, text=t('process_picker.from_process'),
                   command=self._add_from_process).pack(side='left')
        ttk.Button(btn_frame, text=t('ignore.remove_selected'),
                   command=self._remove_selected).pack(side='left', padx=4)
        ttk.Button(btn_frame, text=t('ignore.clear_all'),
                   command=self._clear_all).pack(side='left', padx=4)

        self._populate()

    def _populate(self):
        for item in self._tree.get_children():
            self._tree.delete(item)
        ignored = self._config.ignored_apps
        self._count_label.configure(text=t('ignore.count', count=len(ignored)))
        for item in ignored:
            self._tree.insert('', 'end', iid=item.get('exe_path', ''),
                              values=(
                                  item.get('app_name', ''),
                                  item.get('exe_path', ''),
                                  item.get('ignored_at', '')[:16],
                              ))

    def _remove_selected(self):
        sel = self._tree.selection()
        if not sel:
            return
        for exe_path in sel:
            self._config.remove_ignored_app(exe_path)
            if self._data_store:
                self._data_store.remove_ignored_app(exe_path)
        self._populate()

    def _clear_all(self):
        for item in self._config.ignored_apps:
            exe_path = item.get('exe_path', '')
            if exe_path:
                self._data_store.remove_ignored_app(exe_path)
        self._config.set('ignored_apps', [])
        self._config.save()
        self._populate()

    def _add_from_process(self):
        """从当前运行进程中选择要忽略的应用"""
        picker = ProcessPicker(self)
        self.wait_window(picker)
        if picker.result:
            exe_path = picker.result['exe']
            app_name = picker.result['name']
            self._config.add_ignored_app(exe_path, app_name)
            self._populate()

    def apply(self):
        pass
