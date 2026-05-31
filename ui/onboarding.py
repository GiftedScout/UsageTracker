"""
First-run onboarding window for UsageTracker (dark theme).
Shows a welcome screen with gradient background and guides initial setup.
"""

import tkinter as tk
import logging
from pathlib import Path

from src.i18n import t
from .styled_widgets import (
    StyledButton, StyledLabel, Card, draw_gradient, create_rounded_rect,
    BG_DARK, BG_GRADIENT, CARD_BG, ACCENT_BLUE,
    TEXT_WHITE, TEXT_GRAY, BTN_SECONDARY, BORDER_COLOR, INPUT_BG,
)

logger = logging.getLogger(__name__)

# Helper duplicates from tab_general (avoid circular imports)
_TRANSLATION_PAIRS = [('zh-CN', '中文'), ('en', 'English')]


def _translated_values(pairs):
    from src.i18n import t as _t
    result = []
    for _, val in pairs:
        tr = _t(val)
        result.append(tr if tr != val else val)
    return result


def _key_to_display(pairs, key_val):
    from src.i18n import t as _t
    for k, val in pairs:
        if k == key_val:
            tr = _t(val)
            return tr if tr != val else val
    return key_val


def _display_to_key(pairs, display_val):
    from src.i18n import t as _t
    for k, val in pairs:
        tr = _t(val)
        text = tr if tr != val else val
        if text == display_val:
            return k
    return display_val


class OnboardingWindow:
    """First-run onboarding window (dark theme, gradient background)."""

    WIN_W = 520
    WIN_H = 520

    def __init__(self, parent, config_manager, startup_manager):
        self._config = config_manager
        self._startup = startup_manager

        # parent 必须是已有的 Tk 根，我们用 Toplevel 避免独占根窗口
        self._window = tk.Toplevel(parent)
        self._window.title(t('onboarding.title'))
        self._window.geometry(f'{self.WIN_W}x{self.WIN_H}')
        self._window.resizable(False, False)

        # Allow close (simply works as dismiss)
        self._window.protocol('WM_DELETE_WINDOW', self._on_close)

        # 设置窗口图标
        self._set_window_icon()

        # Center
        self._window.withdraw()
        self._window.update_idletasks()
        x = (self._window.winfo_screenwidth() - self.WIN_W) // 2
        y = (self._window.winfo_screenheight() - self.WIN_H) // 2
        self._window.geometry(f'+{x}+{y}')
        self._window.deiconify()

        self._build()
        try:
            self._window.grab_set()
        except Exception:
            pass

    def wait(self):
        """等待窗口关闭"""
        self._window.wait_window()

    def _build(self):
        """Build onboarding UI with gradient background."""
        # Gradient canvas root
        self._root_canvas = tk.Canvas(self._window, highlightthickness=0)
        self._root_canvas.pack(fill='both', expand=True)

        def _on_resize(event):
            draw_gradient(self._root_canvas, event.width, event.height,
                          BG_DARK, BG_GRADIENT, 'bg')

        self._root_canvas.bind('<Configure>', _on_resize)

        # Container frame on top
        self._container = tk.Frame(self._root_canvas, bg=BG_DARK)
        self._container.pack(fill='both', expand=True, padx=20, pady=20)

        # Welcome card
        welcome_card = Card(self._container, title=t('onboarding.welcome_title'),
                            title_fg=ACCENT_BLUE)
        welcome_card.pack(fill='x', padx=0, pady=(0, 12))

        desc = StyledLabel(welcome_card.content,
                          text=t('onboarding.description'),
                          fg=TEXT_GRAY, bg=CARD_BG,
                          font=('', 10), justify='left')
        desc.pack(anchor='w')

        # Settings card
        settings_card = Card(self._container,
                            title=t('onboarding.settings_title'),
                            title_fg=ACCENT_BLUE)
        settings_card.pack(fill='x', padx=0, pady=(0, 12))

        sc = settings_card.content
        sc.columnconfigure(1, weight=1)
        row = 0

        # Auto start - with recommendation emphasis
        tk.Label(sc, text=t('general.auto_start'), fg=TEXT_WHITE,
                 bg=CARD_BG, font=('', 10, 'bold')).grid(
            row=row, column=0, sticky='w', padx=(0, 16), pady=(4, 2))
        row += 1
        tk.Label(sc,
                text=t('onboarding.auto_start_recommend'),
                fg=TEXT_GRAY, bg=CARD_BG, font=('', 8), wraplength=400,
                justify='left').grid(
            row=row, column=0, columnspan=2, sticky='w', padx=(0, 16), pady=(0, 4))
        row += 1
        self._auto_start_var = tk.BooleanVar(value=True)  # 默认开启
        tk.Checkbutton(sc, variable=self._auto_start_var,
                      bg=CARD_BG, fg=TEXT_WHITE,
                      selectcolor=INPUT_BG,
                      activebackground=CARD_BG,
                      text=t('onboarding.auto_start_tip')).grid(
            row=row, column=0, columnspan=2, sticky='w', pady=(0, 8))
        row += 1

        # Notifications
        tk.Label(sc, text=t('general.auto_show_report'), fg=TEXT_WHITE,
                 bg=CARD_BG, anchor='w').grid(
            row=row, column=0, sticky='w', padx=(0, 16), pady=4)
        self._auto_report_var = tk.BooleanVar(value=True)
        tk.Checkbutton(sc, variable=self._auto_report_var,
                      bg=CARD_BG, fg=TEXT_WHITE,
                      selectcolor=INPUT_BG,
                      activebackground=CARD_BG).grid(
            row=row, column=1, sticky='w', pady=4)
        row += 1

        # Language
        tk.Label(sc, text=t('general.language'), fg=TEXT_WHITE,
                 bg=CARD_BG, anchor='w').grid(
            row=row, column=0, sticky='w', padx=(0, 16), pady=4)
        from tkinter import ttk
        self._lang_var = tk.StringVar(
            value=_key_to_display(_TRANSLATION_PAIRS, self._config.language))
        lang_combo = ttk.Combobox(sc, textvariable=self._lang_var,
                                  values=_translated_values(_TRANSLATION_PAIRS),
                                  state='readonly', width=14)
        lang_combo.grid(row=row, column=1, sticky='w', pady=4)
        row += 1

        # UI Mode selection
        tk.Label(sc, text=t('settings.title'), fg=TEXT_WHITE,
                 bg=CARD_BG, font=('', 10, 'bold')).grid(
            row=row, column=0, columnspan=2, sticky='w', pady=(8, 2))
        row += 1
        self._ui_mode_var = tk.StringVar(value='rich')
        tk.Radiobutton(sc, text=t('settings.mode_rich'),
                       variable=self._ui_mode_var, value='rich',
                       bg=CARD_BG, fg=TEXT_WHITE, selectcolor=INPUT_BG,
                       activebackground=CARD_BG).grid(
            row=row, column=0, columnspan=2, sticky='w', pady=2)
        row += 1
        tk.Radiobutton(sc, text=t('settings.mode_simple'),
                       variable=self._ui_mode_var, value='simple',
                       bg=CARD_BG, fg=TEXT_WHITE, selectcolor=INPUT_BG,
                       activebackground=CARD_BG).grid(
            row=row, column=0, columnspan=2, sticky='w', pady=2)
        row += 1

        # Get Started button at bottom
        get_started = StyledButton(self._container,
                                   text=t('onboarding.get_started'),
                                   command=self._on_get_started,
                                   bg_normal=ACCENT_BLUE, fg_normal=TEXT_WHITE,
                                   bg_active='#3da0ff',
                                   bg_pressed='#1873cc',
                                   height=34)
        get_started.pack(side='bottom', anchor='se', pady=(10, 0))

    def _on_get_started(self):
        self._config.auto_start = self._auto_start_var.get()
        self._config.auto_show_daily_report = self._auto_report_var.get()
        new_lang = _display_to_key(_TRANSLATION_PAIRS, self._lang_var.get())
        self._config.language = new_lang
        self._config.ui_mode = self._ui_mode_var.get()

        if not self._is_test_run():
            if self._auto_start_var.get():
                self._startup.enable_startup()
            else:
                self._startup.disable_startup()

        self._config.first_run = False
        self._config.save()
        logger.info('Onboarding completed, first_run set to False')
        self._window.destroy()

    def _on_close(self):
        """关闭引导窗口 = 退出程序（用户明确拒绝设置）"""
        # 设置 first_run 保持 true，下次启动仍会显示引导
        self._window.destroy()

    @staticmethod
    def _get_icon_path() -> str:
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

    def _is_test_run(self):
        import sys as _sys
        from pathlib import Path as _Path
        if getattr(_sys, 'frozen', False):
            _exe = _Path(_sys.executable)
            return 'dist' in _exe.parent.parts
        return False
