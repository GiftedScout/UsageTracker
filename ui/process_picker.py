"""进程选择器弹窗：列举当前运行进程，供用户选择后返回路径/进程名"""

import tkinter as tk
from tkinter import ttk
import logging
import threading

from src.i18n import t

logger = logging.getLogger(__name__)


class ProcessPicker(tk.Toplevel):
    """进程选择器对话框。

    使用方式::

        picker = ProcessPicker(parent)
        parent.wait_window(picker)
        result = picker.result  # None 或 {'name': str, 'exe': str, 'pid': int}

    参数
    ----
    exe_only : bool
        若为 True，result['exe'] 只返回进程文件名（不含路径），适合游戏管理。
    """

    def __init__(self, parent, exe_only: bool = False):
        super().__init__(parent)
        self.title(t('process_picker.title'))
        self.geometry('620x440')
        self.resizable(True, True)
        self.minsize(480, 320)
        self.transient(parent)
        self.grab_set()

        self._exe_only = exe_only
        self.result = None
        self._all_procs = []   # [(display_str, name, exe, pid)]

        self._build()
        self._load_processes()

    # ------------------------------------------------------------------
    # UI 构建
    # ------------------------------------------------------------------
    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # 搜索栏
        search_frame = ttk.Frame(self)
        search_frame.grid(row=0, column=0, sticky='ew', padx=10, pady=(10, 4))
        search_frame.columnconfigure(1, weight=1)
        ttk.Label(search_frame, text=t('process_picker.search')).grid(
            row=0, column=0, padx=(0, 6))
        self._search_var = tk.StringVar()
        self._search_var.trace_add('write', lambda *_: self._filter())
        ttk.Entry(search_frame, textvariable=self._search_var).grid(
            row=0, column=1, sticky='ew')

        # 进程列表
        list_frame = ttk.Frame(self)
        list_frame.grid(row=1, column=0, sticky='nsew', padx=10, pady=2)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        cols = ('name', 'pid', 'exe')
        self._tree = ttk.Treeview(list_frame, columns=cols,
                                  show='headings', selectmode='browse')
        self._tree.heading('name', text=t('process_picker.col_name'))
        self._tree.heading('pid',  text=t('process_picker.col_pid'))
        self._tree.heading('exe',  text=t('process_picker.col_exe'))
        self._tree.column('name', width=150, stretch=False)
        self._tree.column('pid',  width=60,  stretch=False)
        self._tree.column('exe',  width=340)
        self._tree.bind('<Double-1>', lambda _: self._ok())

        vsb = ttk.Scrollbar(list_frame, orient='vertical',
                            command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')

        # 状态栏
        self._status_var = tk.StringVar(value=t('process_picker.loading'))
        ttk.Label(self, textvariable=self._status_var,
                  foreground='#888').grid(
            row=2, column=0, sticky='w', padx=12, pady=2)

        # 按钮区
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=3, column=0, pady=(4, 10))
        ttk.Button(btn_frame, text=t('process_picker.refresh'),
                   command=self._load_processes).pack(side='left', padx=8)
        ttk.Button(btn_frame, text=t('settings.ok'),
                   command=self._ok).pack(side='left', padx=8)
        ttk.Button(btn_frame, text=t('settings.cancel'),
                   command=self.destroy).pack(side='left', padx=8)

    # ------------------------------------------------------------------
    # 进程枚举（后台线程，避免 UI 卡顿）
    # ------------------------------------------------------------------
    def _load_processes(self):
        self._status_var.set(t('process_picker.loading'))
        for item in self._tree.get_children():
            self._tree.delete(item)
        threading.Thread(target=self._fetch_procs,
                         daemon=True, name='proc-picker-fetch').start()

    def _fetch_procs(self):
        try:
            import psutil
        except ImportError:
            self.after(0, lambda: self._status_var.set(
                t('process_picker.psutil_missing')))
            return

        procs = {}
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                pid  = proc.info['pid']
                name = proc.info['name'] or ''
                exe  = proc.info['exe'] or ''
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            if not name or not exe:
                continue
            # 去重：相同 exe 只保留第一个 PID（减少噪音）
            key = exe.lower()
            if key not in procs:
                procs[key] = (name, exe, pid)

        result = sorted(procs.values(), key=lambda x: x[0].lower())
        self.after(0, lambda: self._set_procs(result))

    def _set_procs(self, procs):
        """在主线程中更新列表"""
        import os
        self._all_procs = []
        for name, exe, pid in procs:
            display_exe = os.path.basename(exe) if self._exe_only else exe
            self._all_procs.append((name, display_exe, pid, exe))
        self._filter()
        self._status_var.set(
            t('process_picker.count', count=len(self._all_procs)))

    # ------------------------------------------------------------------
    # 搜索过滤
    # ------------------------------------------------------------------
    def _filter(self):
        kw = self._search_var.get().strip().lower()
        for item in self._tree.get_children():
            self._tree.delete(item)
        for name, display_exe, pid, _raw_exe in self._all_procs:
            if kw and kw not in name.lower() and kw not in display_exe.lower():
                continue
            self._tree.insert('', 'end', values=(name, pid, display_exe))

    # ------------------------------------------------------------------
    # 确认选择
    # ------------------------------------------------------------------
    def _ok(self):
        sel = self._tree.selection()
        if not sel:
            return
        vals = self._tree.item(sel[0], 'values')
        if not vals:
            return
        name, pid, display_exe = vals[0], vals[1], vals[2]
        # 找回 raw exe（完整路径）
        raw_exe = display_exe  # fallback
        for n, de, p, re in self._all_procs:
            if str(p) == str(pid) and n == name:
                raw_exe = re
                break
        self.result = {
            'name': name,
            'exe':  display_exe if self._exe_only else raw_exe,
            'pid':  int(pid),
        }
        self.destroy()
