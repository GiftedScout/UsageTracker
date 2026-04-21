"""运行日志与反馈标签页：查看运行日志（支持级别筛选）+ 导出反馈包"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from datetime import datetime
from pathlib import Path

from src.i18n import t

logger = logging.getLogger(__name__)


class TabFeedback(ttk.Frame):
    """运行日志与问题反馈"""

    def __init__(self, parent, crash_handler=None):
        super().__init__(parent)
        self._crash_handler = crash_handler
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)
        pad = {'padx': 12, 'pady': 6, 'sticky': 'ew'}

        # 运行日志
        ttk.Label(self, text=t('feedback.logs'), font=('', 9, 'bold')).grid(
            row=0, column=0, sticky='w', padx=12, pady=(8, 4))

        # 筛选控件
        filter_frame = ttk.Frame(self)
        filter_frame.grid(row=1, column=0, sticky='ew', padx=12, pady=2)
        ttk.Label(filter_frame, text=t('feedback.level')).pack(side='left')
        self._level_var = tk.StringVar(value='ALL')
        level_combo = ttk.Combobox(filter_frame, textvariable=self._level_var,
                                   values=['ALL', 'INFO', 'WARNING', 'ERROR'],
                                   state='readonly', width=8)
        level_combo.pack(side='left', padx=4)
        level_combo.bind('<<ComboboxSelected>>', lambda e: self._populate())

        ttk.Label(filter_frame, text=t('feedback.date')).pack(side='left')
        self._date_var = tk.StringVar()
        self._date_combo = ttk.Combobox(filter_frame, textvariable=self._date_var,
                                        state='readonly', width=12)
        self._date_combo.pack(side='left', padx=4)
        self._date_combo.bind('<<ComboboxSelected>>', lambda e: self._populate())

        self._count_label = ttk.Label(self, text='')
        self._count_label.grid(row=2, column=0, sticky='w', padx=24, pady=2)

        # 日志内容区（Text + 滚动条）
        text_frame = ttk.Frame(self)
        text_frame.grid(row=3, column=0, sticky='nsew', padx=12, pady=4)
        self.rowconfigure(3, weight=1)

        self._text = tk.Text(text_frame, wrap='none', font=('Consolas', 9),
                             state='disabled', bg='#1e1e1e', fg='#d4d4d4',
                             insertbackground='#d4d4d4', selectbackground='#264f78')
        y_scroll = ttk.Scrollbar(text_frame, orient='vertical', command=self._text.yview)
        x_scroll = ttk.Scrollbar(text_frame, orient='horizontal', command=self._text.xview)
        self._text.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        self._text.grid(row=0, column=0, sticky='nsew')
        y_scroll.grid(row=0, column=1, sticky='ns')
        x_scroll.grid(row=1, column=0, sticky='ew')
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        # 配置 tag 用于着色
        self._text.tag_configure('info', foreground='#9cdcfe')
        self._text.tag_configure('warning', foreground='#dcdcaa')
        self._text.tag_configure('error', foreground='#f48771')
        self._text.tag_configure('crash', foreground='#f48771', font=('Consolas', 9, 'bold'))

        # 日志文件列表
        log_btn_frame = ttk.Frame(self)
        log_btn_frame.grid(row=4, column=0, sticky='ew', padx=12, pady=4)
        ttk.Button(log_btn_frame, text=t('feedback.clear'), command=self._clear_logs).pack(side='left')
        ttk.Button(log_btn_frame, text=t('feedback.refresh'), command=self._populate).pack(side='left', padx=4)

        ttk.Separator(self, orient='horizontal').grid(row=5, column=0, sticky='ew', padx=12, pady=8)

        # 反馈包
        ttk.Label(self, text=t('feedback.issue'), font=('', 9, 'bold')).grid(
            row=6, column=0, sticky='w', padx=12, pady=(4, 2))
        ttk.Label(self, text=t('feedback.issue_desc'),
                  wraplength=450, foreground='#666').grid(row=7, column=0, padx=24, pady=2, sticky='w')

        ttk.Button(self, text=t('feedback.generate'), command=self._generate_feedback).grid(
            row=8, column=0, padx=12, pady=8, sticky='w')

        self._log_files: list[dict] = []
        self._populate()

    def _get_log_dirs(self) -> tuple[Path, Path]:
        """获取日志目录和崩溃日志目录"""
        try:
            from ..src.constants import LOG_DIR, CRASH_LOG_DIR
            return LOG_DIR, CRASH_LOG_DIR
        except Exception:
            return Path(''), Path('')

    def _scan_logs(self) -> list[dict]:
        """扫描所有日志文件"""
        log_dir, crash_dir = self._get_log_dirs()
        logs = []
        # 运行日志
        if log_dir.exists():
            for f in sorted(log_dir.glob('usage_tracker_*.log'), reverse=True):
                try:
                    stat = f.stat()
                    logs.append({
                        'filename': f.name, 'path': str(f), 'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'type': 'log',
                    })
                except Exception:
                    pass
        # 崩溃日志
        if crash_dir.exists():
            for f in sorted(crash_dir.glob('crash_*.log'), reverse=True):
                try:
                    stat = f.stat()
                    logs.append({
                        'filename': f.name, 'path': str(f), 'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'type': 'crash',
                    })
                except Exception:
                    pass
        return logs

    def _populate(self):
        """加载日志文件列表并显示最新日志内容"""
        self._log_files = self._scan_logs()

        # 更新日期下拉
        dates = []
        for log in self._log_files:
            if log['type'] == 'log':
                name = log['filename']
                if '_' in name and name.endswith('.log'):
                    d = name.replace('usage_tracker_', '').replace('.log', '')
                    if len(d) == 8:
                        dates.append(f'{d[:4]}-{d[4:6]}-{d[6:]}')

        current_date = self._date_var.get()
        self._date_combo['values'] = dates
        if dates:
            if current_date not in dates:
                self._date_var.set(dates[0])
        else:
            self._date_var.set('')

        # 找到对应日期的日志文件 + 所有崩溃日志
        target_date = self._date_var.get().replace('-', '')
        selected = None
        crash_logs = []
        for log in self._log_files:
            if log['type'] == 'log' and target_date in log['filename']:
                selected = log
                break
            if log['type'] == 'crash':
                crash_logs.append(log)

        if not selected and self._log_files:
            selected = self._log_files[0]

        # 显示日志内容
        self._text.configure(state='normal')
        self._text.delete('1.0', 'end')

        level_filter = self._level_var.get()
        line_count = 0

        if selected:
            try:
                with open(selected['path'], 'r', encoding='utf-8') as f:
                    for line in f:
                        stripped = line.rstrip('\n')
                        if level_filter != 'ALL':
                            tag = self._get_line_tag(stripped)
                            if tag and tag != level_filter.lower():
                                continue
                        tag = self._get_line_tag(stripped) or 'info'
                        if selected['type'] == 'crash':
                            tag = 'crash'
                        self._text.insert('end', stripped + '\n', tag)
                        line_count += 1
            except Exception as e:
                self._text.insert('end', t('feedback.read_failed', error=e) + '\n', 'error')
        else:
            self._text.insert('end', t('feedback.no_logs'), 'info')

        # 追加崩溃日志
        for cl in crash_logs[:5]:
            self._text.insert('end', f'\n{"="*60}\n', 'crash')
            self._text.insert('end', f'[crash] {cl["filename"]}\n', 'crash')
            try:
                with open(cl['path'], 'r', encoding='utf-8') as f:
                    for line in f:
                        self._text.insert('end', line.rstrip('\n') + '\n', 'crash')
                        line_count += 1
            except Exception:
                pass

        self._text.configure(state='disabled')

        total_size = sum(l['size'] for l in self._log_files)
        size_str = f'{total_size / 1024:.1f} KB' if total_size >= 1024 else f'{total_size} B'
        self._count_label.configure(text=t('feedback.count', files=len(self._log_files), size=size_str, lines=line_count))

    @staticmethod
    def _get_line_tag(line: str) -> str:
        """根据日志行内容判断级别"""
        if '[ERROR]' in line or '[CRITICAL]' in line:
            return 'error'
        if '[WARNING]' in line:
            return 'warning'
        if '[INFO]' in line:
            return 'info'
        return ''

    def _clear_logs(self):
        if not messagebox.askyesno(t('dialog.confirm'), t('feedback.clear_confirm')):
            return
        log_dir, crash_dir = self._get_log_dirs()
        for log in self._log_files:
            try:
                Path(log['path']).unlink()
            except Exception:
                pass
        self._populate()

    def _generate_feedback(self):
        try:
            from ..src.constants import CRASH_LOG_DIR, CONFIG_PATH, LOG_DIR, FEEDBACK_DIR
            from ..src.version import VERSION
            import zipfile, os, json
        except ImportError:
            messagebox.showerror(t('dialog.error'), t('feedback.module_error'))
            return

        FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_path = FEEDBACK_DIR / f'feedback_{ts}.zip'

        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                # 版本信息
                zf.writestr('version.txt', f'UsageTracker {VERSION}\n'
                            f'Time: {datetime.now().isoformat()}\n'
                            f'Python: {__import__("sys").version}\n')
                # 运行日志
                if LOG_DIR.exists():
                    for log_file in LOG_DIR.glob('usage_tracker_*.log'):
                        zf.write(log_file, f'logs/{log_file.name}')
                # 崩溃日志
                if CRASH_LOG_DIR.exists():
                    for log_file in CRASH_LOG_DIR.glob('crash_*.log'):
                        zf.write(log_file, f'crash_logs/{log_file.name}')
                # 配置快照（去除敏感信息）
                if CONFIG_PATH.exists():
                    cfg = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
                    cfg.pop('ignored_apps', None)
                    cfg.pop('custom_categories', None)
                    zf.writestr('config_snapshot.json', json.dumps(cfg, ensure_ascii=False, indent=2))
            messagebox.showinfo(t('dialog.done'), t('feedback.feedback_done', path=zip_path))
        except Exception as e:
            messagebox.showerror(t('dialog.error'), t('feedback.feedback_failed', error=e))

    def apply(self):
        pass
