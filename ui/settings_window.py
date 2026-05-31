"""设置主窗口：精美模式（左 Tab 侧栏 + 右内容区，深色渐变背景）"""

import tkinter as tk
import logging
from pathlib import Path

from src.i18n import t
from src.version import VERSION

from .tab_general import TabGeneral
from .tab_categories import TabCategories
from .tab_browsers import TabBrowsers
from .tab_games import TabGames
from .tab_ignore import TabIgnore
from .tab_database import TabDatabase
from .tab_feedback import TabFeedback
from .styled_widgets import (
    StyledButton, StyledLabel, StyledFrame, Card,
    SidebarButton,
    BG_DARK, BG_GRADIENT, SIDEBAR_BG, CARD_BG,
    ACCENT_BLUE, TEXT_WHITE, TEXT_GRAY, BTN_SECONDARY,
)

logger = logging.getLogger(__name__)

# Tab configuration: (translation key, icon, class)
SIDEBAR_ITEMS = [
    ('settings.general',    '⚙', TabGeneral),
    ('settings.categories', '📁', TabCategories),
    ('settings.browsers',   '🌐', TabBrowsers),
    ('settings.games',      '🎮', TabGames),
    ('settings.ignore',     '🚫', TabIgnore),
    ('settings.database',   '🗄', TabDatabase),
    ('settings.feedback',   '📝', TabFeedback),
]


class SettingsWindow:
    """设置窗口管理器（精美模式：左侧边栏 + 右侧内容区）"""

    WIN_W = 760
    WIN_H = 560

    def __init__(self, parent, config_manager, startup_manager,
                 app_classifier, data_store, crash_handler=None):
        self._config = config_manager
        self._startup = startup_manager
        self._classifier = app_classifier
        self._data_store = data_store
        self._crash_handler = crash_handler

        self._window = tk.Toplevel(parent) if parent else tk.Tk()
        self._window.title(t('settings.title'))
        self._window.geometry(f'{self.WIN_W}x{self.WIN_H}')
        self._window.resizable(True, True)
        self._window.protocol('WM_DELETE_WINDOW', self._on_cancel)

        # 设置窗口图标
        self._set_window_icon()

        # Center
        if not parent:
            self._window.withdraw()
            self._window.update_idletasks()
            x = (self._window.winfo_screenwidth() - self.WIN_W) // 2
            y = (self._window.winfo_screenheight() - self.WIN_H) // 2
            self._window.geometry(f'{self.WIN_W}x{self.WIN_H}+{x}+{y}')
            self._window.deiconify()

        self._tabs = []
        self._current_tab = 0
        self._set_window_icon()
        self._build()
        self._window.grab_set()

    @staticmethod
    def _get_icon_path() -> str:
        """获取 icon.ico 的路径（支持开发模式和打包模式）"""
        import sys
        if getattr(sys, 'frozen', False):
            base = Path(sys._MEIPASS)
        else:
            base = Path(__file__).resolve().parent.parent
        ico = base / 'assets' / 'icon.ico'
        return str(ico) if ico.exists() else ''

    def _set_window_icon(self):
        ico = self._get_icon_path()
        if ico:
            try:
                self._window.iconbitmap(ico)
            except Exception:
                pass

    def _build(self):
        """Build the rich mode UI."""
        ui_mode = self._config.ui_mode
        if ui_mode == 'rich':
            self._build_rich()
        else:
            self._build_simple()

    def _build_simple(self):
        """精简模式：复用原有 ttk.Notebook 逻辑（略）—— 暂不迁移"""
        self._build_original_notebook()

    def _build_original_notebook(self):
        """Fallback to original ttk.Notebook layout."""
        from tkinter import ttk
        nb = ttk.Notebook(self._window)
        nb.pack(fill='both', expand=True, padx=8, pady=(8, 0))

        tabs_data = [
            (t('settings.general'), TabGeneral),
            (t('settings.categories'), TabCategories),
            (t('settings.browsers'), TabBrowsers),
            (t('settings.games'), TabGames),
            (t('settings.ignore'), TabIgnore),
            (t('settings.database'), TabDatabase),
            (t('settings.feedback'), TabFeedback),
        ]

        for label, cls in tabs_data:
            frame = cls(nb, **self._get_tab_kwargs(cls))
            nb.add(frame, text=label)
            self._tabs.append(frame)

        btn_frame = ttk.Frame(self._window)
        btn_frame.pack(fill='x', padx=8, pady=8)
        btn_frame.columnconfigure(0, weight=1)

        ttk.Button(btn_frame, text=t('settings.ok'), width=8,
                   command=self._on_ok).grid(row=0, column=1, padx=4)
        ttk.Button(btn_frame, text=t('settings.cancel'), width=8,
                   command=self._on_cancel).grid(row=0, column=2, padx=4)
        ttk.Button(btn_frame, text=t('settings.apply'), width=8,
                   command=self._on_apply).grid(row=0, column=3, padx=4)

    def _build_rich(self):
        """精美模式：深色背景 + 左侧边栏 + 右侧内容区"""
        
        # ── Apply dark ttk style for all tab widgets ──────
        from .styled_widgets import setup_dark_ttk_style
        setup_dark_ttk_style()

        # ── Root container (Frame, not Canvas — Canvas 布局不可靠) ──
        root_frame = tk.Frame(self._window, bg=BG_DARK)
        root_frame.pack(fill='both', expand=True)

        # ── Sidebar frame ─────────────────────────────────
        sidebar_frame = tk.Frame(root_frame, bg=SIDEBAR_BG,
                                 width=SidebarButton.SIDEBAR_W)
        sidebar_frame.pack(side='left', fill='y')
        sidebar_frame.pack_propagate(False)

        # ── Right content area ────────────────────────────
        self._content_bg = tk.Frame(root_frame, bg=BG_DARK)
        self._content_bg.pack(side='left', fill='both', expand=True)

        self._sidebar_frame = sidebar_frame
        self._build_sidebar()
        self._build_content_area()

        # Switch to tab 0
        self._switch_tab(0)

        # ── Mode switch button in top-right corner ────────
        self._mode_btn = StyledButton(self._window,
                                      text=self._get_mode_btn_text(),
                                      command=self._toggle_mode,
                                      bg_normal=BTN_SECONDARY,
                                      fg_normal=TEXT_WHITE,
                                      bg_active=ACCENT_BLUE,
                                      bg_pressed='#1873cc')
        self._mode_btn.place(x=self.WIN_W - 110, y=8)

    def _build_sidebar(self):
        """创建左侧边栏（带发光指示器的垂直 Tab 列表）"""
        # Header space
        header = tk.Label(self._sidebar_frame,
                          text=t('settings.title'),
                          font=('', 12, 'bold'),
                          fg=TEXT_WHITE, bg=SIDEBAR_BG,
                          anchor='center')
        header.pack(fill='x', pady=(16, 12))

        # Separator
        sep = tk.Frame(self._sidebar_frame, height=1, bg='#1a2a40')
        sep.pack(fill='x', padx=10, pady=(0, 8))

        # Tab buttons
        self._sidebar_buttons = []
        self._tab_content_frames = []

        for i, (key, icon, cls) in enumerate(SIDEBAR_ITEMS):
            label = t(key)
            btn = SidebarButton(
                self._sidebar_frame,
                text=label,
                icon=icon,
                command=self._switch_tab,
                index=i,
                active=(i == 0)
            )
            btn.pack(side='top', padx=6, pady=2)
            self._sidebar_buttons.append(btn)

            # Create content frame (hidden initially)
            content_frame = tk.Frame(self._content_bg, bg=BG_DARK)
            # Build the actual tab UI inside
            kwargs = self._get_tab_kwargs(cls)
            tab_instance = cls(content_frame, **kwargs)
            tab_instance.pack(fill='both', expand=True)
            self._tabs.append(tab_instance)
            self._tab_content_frames.append(content_frame)

        # Bottom spacer
        tk.Frame(self._sidebar_frame, bg=SIDEBAR_BG).pack(
            side='bottom', fill='x', pady=4)

    def _build_content_area(self):
        """Create content area wrapper for cards."""
        # A container to hold all pages; only one visible at a time
        self._content_pages = {}

    def _get_content_page(self, index):
        """Get or create a content page for the tab at index."""
        if index not in self._content_pages:
            card = Card(self._content_bg, title='')
            self._content_pages[index] = card
        return self._content_pages[index]

    def _switch_tab(self, index):
        """Switch to the tab at the given index."""
        if index == self._current_tab:
            return

        # Update sidebar buttons
        for i, btn in enumerate(self._sidebar_buttons):
            btn.set_active(i == index)

        # Hide all content frames
        for i, frame in enumerate(self._tab_content_frames):
            if i == index:
                frame.pack(fill='both', expand=True)
            else:
                frame.pack_forget()

        self._current_tab = index

    def _get_mode_btn_text(self):
        """文本：切换到精简模式/切换回精美模式"""
        cur = self._config.ui_mode
        if cur == 'rich':
            return '精简模式'
        else:
            return '精美模式'

    def _toggle_mode(self):
        """切换 UI 模式"""
        cur = self._config.ui_mode
        new = 'simple' if cur == 'rich' else 'rich'
        self._config.ui_mode = new
        self._config.save()
        logger.info(f'UI mode switched: {cur} -> {new}')
        # 触发回调清理 settings_root（由 main.py 设置）
        if hasattr(self, '_on_switched_cb') and self._on_switched_cb:
            self._on_switched_cb()
        else:
            self._window.destroy()

    # ── Tab kwargs ──────────────────────────────────────

    def _get_tab_kwargs(self, cls):
        if cls is TabGeneral:
            return {'config_manager': self._config,
                    'startup_manager': self._startup}
        elif cls is TabCategories:
            return {'config_manager': self._config,
                    'app_classifier': self._classifier}
        elif cls is TabBrowsers:
            return {'config_manager': self._config,
                    'app_classifier': self._classifier}
        elif cls is TabGames:
            return {'app_classifier': self._classifier,
                    'config_manager': self._config}
        elif cls is TabIgnore:
            return {'config_manager': self._config,
                    'data_store': self._data_store}
        elif cls is TabDatabase:
            return {'config_manager': self._config,
                    'data_store': self._data_store}
        elif cls is TabFeedback:
            return {'crash_handler': self._crash_handler}
        return {}

    # ── Actions ─────────────────────────────────────────

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

    def _reposition_widgets(self, width, height):
        """Handle resize for mode button positioning."""
        try:
            self._mode_btn.place(x=width - 110, y=8)
        except Exception:
            pass

    def show(self):
        self._window.focus_force()
        return self._window

    def wait(self):
        self._window.wait_window()
