"""项目目录标签页：管理常用开发/工作项目目录。"""

import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path
import logging

from src.i18n import t

logger = logging.getLogger(__name__)


class TabProjects(ttk.Frame):
    """项目目录管理。"""

    def __init__(self, parent, config_manager, app_classifier=None):
        super().__init__(parent)
        self._config = config_manager
        self._classifier = app_classifier
        self._dir_var = tk.StringVar()
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        ttk.Label(self, text=t('projects.dirs'), font=('', 9, 'bold')).grid(
            row=0, column=0, sticky='w', padx=12, pady=(8, 4))
        ttk.Label(self, text=t('projects.desc'), foreground='#888').grid(
            row=1, column=0, sticky='w', padx=12, pady=(0, 4))

        self._tree = ttk.Treeview(self, columns=('path',), show='headings', height=10)
        self._tree.heading('path', text=t('projects.path'))
        self._tree.column('path', width=520)
        self._tree.grid(row=2, column=0, sticky='nsew', padx=12, pady=4)

        form = ttk.Frame(self)
        form.grid(row=3, column=0, sticky='ew', padx=12, pady=4)
        form.columnconfigure(1, weight=1)
        ttk.Label(form, text=t('projects.path')).grid(row=0, column=0, sticky='w')
        ttk.Entry(form, textvariable=self._dir_var).grid(row=0, column=1, sticky='ew', padx=4)
        ttk.Button(form, text=t('projects.browse'), command=self._browse).grid(row=0, column=2, padx=(0, 4))
        ttk.Button(form, text=t('projects.add'), command=self._add_dir).grid(row=0, column=3)

        btns = ttk.Frame(self)
        btns.grid(row=4, column=0, sticky='ew', padx=12, pady=(0, 8))
        ttk.Button(btns, text=t('projects.remove_selected'), command=self._remove_selected).pack(side='left')
        ttk.Button(btns, text=t('projects.refresh'), command=self._populate).pack(side='left', padx=4)

        self._suggest_label = ttk.Label(self, text='', foreground='#888', wraplength=650, justify='left')
        self._suggest_label.grid(row=5, column=0, sticky='ew', padx=12, pady=(0, 8))

        self._populate()

    def _populate(self):
        for item in self._tree.get_children():
            self._tree.delete(item)
        for d in self._config.project_dirs:
            self._tree.insert('', 'end', iid=d, values=(d,))
        self._render_suggestions()

    def _render_suggestions(self):
        suggestions = []
        if self._classifier and hasattr(self._classifier, 'get_suggestions'):
            try:
                suggestions = self._classifier.get_suggestions()[:5]
            except Exception as e:
                logger.debug('load project suggestions failed: %s', e)
        if not suggestions:
            self._suggest_label.configure(text=t('projects.no_suggestions'))
            return
        parts = []
        for item in suggestions:
            name = item.get('app_name') or item.get('exe_path') or ''
            secs = int(item.get('duration_seconds') or 0)
            minutes = max(1, secs // 60) if secs else 0
            parts.append(f'{name} ({minutes} min)')
        self._suggest_label.configure(text=t('projects.suggestions') + ' ' + ', '.join(parts))

    def _browse(self):
        path = filedialog.askdirectory(parent=self, title=t('projects.browse'))
        if path:
            self._dir_var.set(path)

    def _add_dir(self):
        d = self._dir_var.get().strip()
        if not d:
            return
        # Keep the original string if the path does not exist yet, but normalize existing paths.
        try:
            d = str(Path(d).expanduser().resolve()) if Path(d).expanduser().exists() else d
        except Exception:
            pass
        if self._config.add_project_dir(d):
            logger.debug('added project directory: %s', d)
        self._dir_var.set('')
        self._populate()

    def _remove_selected(self):
        sel = self._tree.selection()
        if not sel:
            return
        for d in sel:
            self._config.remove_project_dir(d)
        self._populate()

    def apply(self):
        pass
