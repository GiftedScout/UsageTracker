"""分类管理标签页：预设分类 + 用户自定义分类 + 向分类添加程序"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import logging

logger = logging.getLogger(__name__)


class TabCategories(ttk.Frame):
    """分类管理"""

    def __init__(self, parent, config_manager, app_classifier):
        super().__init__(parent)
        self._config = config_manager
        self._classifier = app_classifier
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)

        # 预设分类
        ttk.Label(self, text='预设分类', font=('', 9, 'bold')).grid(
            row=0, column=0, sticky='w', padx=12, pady=(8, 4))
        preset_frame = ttk.Frame(self)
        preset_frame.grid(row=1, column=0, sticky='ew', padx=24, pady=2)
        for i, (cat_id, name) in enumerate([
            ('browser', '浏览器'), ('game', '游戏'), ('other', '其他'),
        ]):
            ttk.Label(preset_frame, text=f'  {name}', foreground='#555').grid(
                row=i // 3, column=i % 3, sticky='w', padx=8)

        ttk.Separator(self, orient='horizontal').grid(
            row=2, column=0, sticky='ew', padx=12, pady=8)

        # 自定义分类
        ttk.Label(self, text='自定义分类', font=('', 9, 'bold')).grid(
            row=3, column=0, sticky='w', padx=12, pady=(4, 2))

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=4, column=0, sticky='ew', padx=12, pady=4)
        ttk.Button(btn_frame, text='添加分类', command=self._add_category).pack(side='left')
        ttk.Button(btn_frame, text='删除选中分类',
                   command=self._remove_category).pack(side='left', padx=4)
        ttk.Separator(btn_frame, orient='vertical').pack(
            side='left', fill='y', padx=8, pady=2)
        ttk.Button(btn_frame, text='添加程序到分类',
                   command=self._add_app_to_selected).pack(side='left')
        ttk.Button(btn_frame, text='移除选中程序',
                   command=self._remove_app_from_selected).pack(side='left', padx=4)

        # 主区域: 上面是分类列表，下面是选中分类的程序列表
        paned = ttk.PanedWindow(self, orient='vertical')
        paned.grid(row=5, column=0, sticky='nsew', padx=12, pady=4)
        self.rowconfigure(5, weight=1)

        # 分类列表
        cat_frame = ttk.LabelFrame(paned, text='自定义分类')
        cols = ('name', 'color', 'apps')
        self._tree = ttk.Treeview(cat_frame, columns=cols, show='headings',
                                  height=5)
        self._tree.heading('name', text='分类名')
        self._tree.heading('color', text='颜色')
        self._tree.heading('apps', text='程序数')
        self._tree.column('name', width=140)
        self._tree.column('color', width=80)
        self._tree.column('apps', width=60)
        self._tree.pack(fill='both', expand=True, padx=4, pady=4)
        self._tree.bind('<<TreeviewSelect>>', self._on_cat_select)
        paned.add(cat_frame, weight=1)

        # 程序列表
        app_frame = ttk.LabelFrame(paned, text='选中分类的程序')
        self._app_tree = ttk.Treeview(app_frame, columns=('exe',),
                                       show='headings', height=4)
        self._app_tree.heading('exe', text='程序路径')
        self._app_tree.column('exe', width=500)
        self._app_tree.pack(fill='both', expand=True, padx=4, pady=4)
        paned.add(app_frame, weight=1)

        self._populate()

    def _populate(self):
        for item in self._tree.get_children():
            self._tree.delete(item)
        for cat in self._config.custom_categories:
            apps = cat.get('apps', [])
            self._tree.insert('', 'end', iid=cat.get('id'),
                              values=(cat.get('name', ''), cat.get('color', '#0078D4'),
                                      len(apps)))

    def _on_cat_select(self, event=None):
        self._app_tree.delete(0, 'end')
        sel = self._tree.selection()
        if not sel:
            return
        cat_id = sel[0]
        for cat in self._config.custom_categories:
            if cat.get('id') == cat_id:
                for app in cat.get('apps', []):
                    self._app_tree.insert('', 'end', values=(app,))
                break

    def _get_selected_cat_id(self) -> str | None:
        sel = self._tree.selection()
        return sel[0] if sel else None

    def _add_category(self):
        dialog = _CategoryDialog(self)
        self.wait_window(dialog)
        if dialog.result:
            name, color = dialog.result
            cat_id = f'custom_{name}_{id(self)}'
            if self._config.add_custom_category(cat_id, name, color):
                self._populate()

    def _remove_category(self):
        sel = self._tree.selection()
        if not sel:
            return
        for item_id in sel:
            self._config.remove_custom_category(item_id)
        self._populate()
        self._app_tree.delete(0, 'end')

    def _add_app_to_selected(self):
        cat_id = self._get_selected_cat_id()
        if not cat_id:
            messagebox.showinfo('提示', '请先选择一个分类')
            return
        path = filedialog.askopenfilename(
            title='选择程序（.exe）',
            filetypes=[('可执行文件', '*.exe'), ('所有文件', '*.*')])
        if not path:
            return
        if self._config.add_app_to_category(cat_id, path):
            self._populate()
            self._on_cat_select()
        else:
            messagebox.showinfo('提示', '该程序已在此分类中')

    def _remove_app_from_selected(self):
        cat_id = self._get_selected_cat_id()
        if not cat_id:
            return
        sel = self._app_tree.selection()
        if not sel:
            return
        for item in sel:
            exe_path = self._app_tree.item(item, 'values')[0]
            self._config.remove_app_from_category(cat_id, exe_path)
        self._populate()
        self._on_cat_select()

    def apply(self):
        pass


class _CategoryDialog(tk.Toplevel):
    """添加自定义分类对话框"""

    def __init__(self, parent):
        super().__init__(parent)
        self.title('添加自定义分类')
        self.geometry('300x160')
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.result = None

        ttk.Label(self, text='分类名称:').grid(row=0, column=0, padx=12, pady=8, sticky='w')
        self._name_var = tk.StringVar()
        ttk.Entry(self, textvariable=self._name_var, width=20).grid(row=0, column=1, padx=12, pady=8)

        ttk.Label(self, text='颜色:').grid(row=1, column=0, padx=12, pady=8, sticky='w')
        self._color = '#0078D4'
        self._color_btn = tk.Button(self, text='    ', bg=self._color, width=4,
                                     command=self._pick_color, relief='solid')
        self._color_btn.grid(row=1, column=1, padx=12, pady=8, sticky='w')

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=12)
        ttk.Button(btn_frame, text='确定', command=self._ok).pack(side='left', padx=8)
        ttk.Button(btn_frame, text='取消', command=self.destroy).pack(side='left', padx=8)

    def _pick_color(self):
        from tkinter import colorchooser
        c = colorchooser.askcolor(initialcolor=self._color, parent=self)
        if c and c[1]:
            self._color = c[1]
            self._color_btn.configure(bg=self._color)

    def _ok(self):
        name = self._name_var.get().strip()
        if name:
            self.result = (name, self._color)
            self.destroy()
