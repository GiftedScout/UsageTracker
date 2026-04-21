"""数据库管理标签页：数据大小、清理、CSV 导出"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import logging
from datetime import date

from src.i18n import t

logger = logging.getLogger(__name__)


class TabDatabase(ttk.Frame):
    """数据库管理"""

    def __init__(self, parent, config_manager, data_store):
        super().__init__(parent)
        self._config = config_manager
        self._data_store = data_store
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)
        pad = {'padx': 12, 'pady': 6, 'sticky': 'ew'}

        # 数据库信息
        ttk.Label(self, text=t('database.info'), font=('', 9, 'bold')).grid(row=0, column=0, **{k: v for k, v in pad.items() if k != 'sticky'})
        self._size_label = ttk.Label(self, text='')
        self._size_label.grid(row=1, column=0, **{k: v for k, v in pad.items() if k != 'sticky'})

        ttk.Separator(self, orient='horizontal').grid(row=2, column=0, sticky='ew', padx=12, pady=8)

        # 数据清理
        ttk.Label(self, text=t('database.cleanup'), font=('', 9, 'bold')).grid(row=3, column=0, **{k: v for k, v in pad.items() if k != 'sticky'})
        retention_frame = ttk.Frame(self)
        retention_frame.grid(row=4, column=0, **{k: v for k, v in pad.items() if k != 'sticky'})
        ttk.Label(retention_frame, text=t('database.retention')).pack(side='left')
        self._retention_var = tk.StringVar(value=self._config.data_retention)
        ret_combo = ttk.Combobox(retention_frame, textvariable=self._retention_var,
                                 values=['unlimited', '1year', '3months', '1month'],
                                 state='readonly', width=12)
        ret_combo.pack(side='left', padx=4)

        clean_frame = ttk.Frame(self)
        clean_frame.grid(row=5, column=0, **{k: v for k, v in pad.items() if k != 'sticky'})
        ttk.Button(clean_frame, text=t('database.cleanup_now'), command=self._cleanup).pack(side='left')

        ttk.Separator(self, orient='horizontal').grid(row=6, column=0, sticky='ew', padx=12, pady=8)

        # 数据导出
        ttk.Label(self, text=t('database.export'), font=('', 9, 'bold')).grid(row=7, column=0, **{k: v for k, v in pad.items() if k != 'sticky'})

        date_frame = ttk.Frame(self)
        date_frame.grid(row=8, column=0, **{k: v for k, v in pad.items() if k != 'sticky'})
        ttk.Label(date_frame, text=t('database.start_date')).pack(side='left')
        self._start_var = tk.StringVar(value='2000-01-01')
        ttk.Entry(date_frame, textvariable=self._start_var, width=12).pack(side='left', padx=4)
        ttk.Label(date_frame, text=t('database.end_date')).pack(side='left')
        self._end_var = tk.StringVar(value=date.today().isoformat())
        ttk.Entry(date_frame, textvariable=self._end_var, width=12).pack(side='left', padx=4)

        ttk.Button(self, text=t('database.export_csv'), command=self._export_csv).grid(
            row=9, column=0, **{k: v for k, v in pad.items() if k != 'sticky'})

        self._refresh_size()

    def _refresh_size(self):
        size = self._data_store.get_database_size()
        if size > 1024 * 1024:
            text = t('database.size', size=f'{size / 1024 / 1024:.2f} MB')
        elif size > 1024:
            text = t('database.size', size=f'{size / 1024:.1f} KB')
        else:
            text = t('database.size', size=f'{size} B')
        self._size_label.configure(text=text)

    def _cleanup(self):
        policy = self._retention_var.get()
        if policy == 'unlimited':
            messagebox.showinfo(t('dialog.hint'), t('database.cleanup_unlimited'))
            return
        if messagebox.askyesno(t('dialog.confirm'), t('database.cleanup_confirm', policy=policy)):
            deleted = self._data_store.cleanup_expired_data(policy)
            self._refresh_size()
            messagebox.showinfo(t('dialog.done'), t('database.cleanup_done', count=deleted))

    def _export_csv(self):
        path = filedialog.asksaveasfilename(
            defaultextension='.csv',
            filetypes=[('CSV', '*.csv')],
            title=t('database.export'),
            initialfile=f'usage_data_{date.today()}.csv')
        if not path:
            return
        try:
            count = self._data_store.export_to_csv(
                path, self._start_var.get(), self._end_var.get())
            messagebox.showinfo(t('dialog.done'), t('database.export_done', count=count, path=path))
        except Exception as e:
            messagebox.showerror(t('database.export_failed'), str(e))

    def apply(self):
        # 保存保留策略
        self._config.data_retention = self._retention_var.get()
        self._config.save()
