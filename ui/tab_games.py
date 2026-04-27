"""游戏目录标签页：显示已识别游戏 + 手动添加/移除"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging

from src.i18n import t
from ui.process_picker import ProcessPicker

logger = logging.getLogger(__name__)


class TabGames(ttk.Frame):
    """游戏目录管理"""

    def __init__(self, parent, app_classifier, config_manager=None):
        super().__init__(parent)
        self._classifier = app_classifier
        self._config = config_manager
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)

        ttk.Label(self, text=t('games.detected'), font=('', 9, 'bold')).grid(
            row=0, column=0, sticky='w', padx=12, pady=(8, 4))

        self._count_label = ttk.Label(self, text='')
        self._count_label.grid(column=0, sticky='w', padx=24, pady=2)

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=2, column=0, sticky='ew', padx=12, pady=4)

        ttk.Button(btn_frame, text=t('games.refresh'),
                   command=self._refresh_games).pack(side='left')

        ttk.Separator(btn_frame, orient='vertical').pack(
            side='left', fill='y', padx=8, pady=2)

        ttk.Label(btn_frame, text=t('games.exe_name')).pack(side='left')
        self._exe_var = tk.StringVar()
        ttk.Entry(btn_frame, textvariable=self._exe_var,
                  width=16).pack(side='left', padx=2)
        ttk.Label(btn_frame, text=t('games.game_name')).pack(side='left')
        self._name_var = tk.StringVar()
        ttk.Entry(btn_frame, textvariable=self._name_var,
                  width=12).pack(side='left', padx=2)
        ttk.Button(btn_frame, text=t('games.add'),
                   command=self._add_game).pack(side='left', padx=2)
        ttk.Button(btn_frame, text=t('process_picker.from_process'),
                   command=self._add_game_from_process).pack(side='left', padx=2)
        ttk.Button(btn_frame, text=t('games.remove_selected'),
                   command=self._remove_game).pack(side='left', padx=2)

        ttk.Label(self, text=t('games.exe_hint'), foreground='#888',
                  wraplength=500, justify='left').grid(
            row=3, column=0, sticky='w', padx=24, pady=(0, 2))

        self._listbox = tk.Listbox(self, height=10)
        self._listbox.grid(column=0, sticky='nsew', padx=12, pady=4)
        self._populate_list()
        self._update_count()

    def _populate_list(self):
        self._listbox.delete(0, 'end')
        for exe, name in sorted(self._classifier.steam_games.items(),
                                key=lambda x: x[1]):
            self._listbox.insert('end', f'[Steam] {name}  ({exe})')
        for exe, name in sorted(self._classifier.extra_games.items(),
                                key=lambda x: x[1]):
            self._listbox.insert('end', f'[{name}] {exe}')

    def _update_count(self):
        s = len(self._classifier.steam_games)
        e = len(self._classifier.extra_games)
        self._count_label.config(
            text=t('games.count', steam=s, extra=e))

    def _add_game(self):
        exe = self._exe_var.get().strip().lower()
        name = self._name_var.get().strip()
        if not exe or not name:
            return
        if not exe.endswith('.exe'):
            exe += '.exe'
        if exe in self._classifier.steam_games or exe in self._classifier.extra_games:
            messagebox.showinfo(t('dialog.hint'), t('games.exists', exe=exe))
            return
        self._classifier.extra_games[exe] = name
        self._classifier._save_cached_games()
        self._exe_var.set('')
        self._name_var.set('')
        self._populate_list()
        self._update_count()

    def _remove_game(self):
        sel = self._listbox.curselection()
        if not sel:
            return
        text = self._listbox.get(sel[0])
        import re
        m = re.search(r'\(([^)]+\.exe)\)', text)
        if m:
            exe_name = m.group(1).lower()
            self._classifier.steam_games.pop(exe_name, None)
        else:
            m2 = re.search(r'\]\s*(\S+\.exe)', text)
            if m2:
                exe_name = m2.group(1).lower()
                self._classifier.extra_games.pop(exe_name, None)
            else:
                return
        self._classifier._save_cached_games()
        self._populate_list()
        self._update_count()

    def _refresh_games(self):
        self._classifier.refresh_all_games()
        self._populate_list()
        self._update_count()

    def _add_game_from_process(self):
        """从当前运行进程中选择游戏（仅取文件名，不需要完整路径）"""
        picker = ProcessPicker(self, exe_only=True)
        self.wait_window(picker)
        if picker.result:
            exe  = picker.result['exe']   # 仅文件名（exe_only=True）
            name = picker.result['name'].replace('.exe', '').replace('_', ' ')
            # 预填到输入框，让用户确认后点"添加"
            self._exe_var.set(exe)
            self._name_var.set(name)

    def apply(self):
        pass
