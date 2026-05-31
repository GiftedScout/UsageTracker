"""
Styled UI components for UsageTracker rich mode (dark theme).
Color scheme derived from assets/banner.png visual analysis.
"""

import tkinter as tk
from tkinter import ttk

# ─── Color palette (from banner.png analysis) ───────────────────────

BG_DARK      = '#0a0f1a'   # Window background (deep navy)
BG_GRADIENT  = '#141b2d'   # Gradient end (slightly lighter)
SIDEBAR_BG   = '#0d1520'   # Left sidebar background
CARD_BG      = '#1a2332'   # Card content area background
ACCENT_BLUE  = '#1E90FF'   # Primary accent / selected tab / buttons
ACCENT_CYAN  = '#00CED1'   # Secondary accent (teal/cyan)
TEXT_WHITE   = '#FFFFFF'   # Primary text
TEXT_GRAY    = '#b0b8c8'   # Secondary/helper text
BTN_SECONDARY = '#3a4a5c'  # Cancel button color
INPUT_BG     = '#1e2a3a'   # Input field backgrounds
BORDER_COLOR = '#2a3a4e'   # Card/input borders
HOVER_BG     = '#1a2a40'   # Sidebar item hover

CORNER_RADIUS = 8          # Global corner radius


def _hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex color string to (R, G, B) tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def draw_gradient(canvas, width: int, height: int,
                  color_top: str, color_bottom: str, tag: str = 'gradient'):
    """Draw a vertical gradient on a Canvas from color_top to color_bottom.
    
    Call this only when the canvas size is known (>0).
    """
    if width < 1 or height < 1:
        return
    canvas.delete(tag)
    c1 = _hex_to_rgb(color_top)
    c2 = _hex_to_rgb(color_bottom)
    for i in range(height):
        ratio = i / height
        r = int(c1[0] * (1 - ratio) + c2[0] * ratio)
        g = int(c1[1] * (1 - ratio) + c2[1] * ratio)
        b = int(c1[2] * (1 - ratio) + c2[2] * ratio)
        color = f'#{r:02x}{g:02x}{b:02x}'
        canvas.create_line(0, i, width, i, fill=color, tags=tag)


def create_rounded_rect(canvas, x1, y1, x2, y2, radius, **kwargs):
    """Draw a rounded rectangle polygon on a canvas.
    
    Returns the canvas item ID.
    """
    points = [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1,
    ]
    return canvas.create_polygon(points, **kwargs, smooth=True)


# ─── Widgets ────────────────────────────────────────────────────────

class StyledFrame(tk.Frame):
    """A simple frame wrapper that sets background color.
    
    For rounded-corner cards, use Card or set a Canvas inside.
    This basic frame just applies the dark theme bg consistently.
    """
    def __init__(self, master, bg=CARD_BG, **kwargs):
        super().__init__(master, bg=bg, **kwargs)


class StyledLabel(tk.Label):
    """A label with dark-theme defaults."""
    def __init__(self, master, text, fg=TEXT_WHITE, bg=CARD_BG,
                 font=None, **kwargs):
        super().__init__(master, text=text, fg=fg, bg=bg,
                         font=font, **kwargs)


class StyledButton(tk.Canvas):
    """A rounded button with hover/press animation (dark theme)."""

    def __init__(self, master, text, command=None,
                 corner_radius=CORNER_RADIUS,
                 bg_normal=ACCENT_BLUE, fg_normal=TEXT_WHITE,
                 bg_active='#3da0ff', fg_active=TEXT_WHITE,
                 bg_pressed='#1873cc', fg_pressed=TEXT_WHITE,
                 bg_disabled=BTN_SECONDARY, fg_disabled=TEXT_GRAY,
                 width=0, height=32, **kwargs):
        super().__init__(master, highlightthickness=0,
                         width=width, height=height, **kwargs)
        self._command = command
        self._cr = corner_radius
        self._bg_n = bg_normal
        self._fg_n = fg_normal
        self._bg_a = bg_active
        self._fg_a = fg_active
        self._bg_p = bg_pressed
        self._fg_p = fg_pressed
        self._bg_d = bg_disabled
        self._fg_d = fg_disabled

        self._state = 'normal'  # normal | active | pressed | disabled

        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        self.bind('<ButtonPress-1>', self._on_press)
        self.bind('<ButtonRelease-1>', self._on_release)
        self.bind('<Configure>', self._redraw)

        self._text_id = self.create_text(0, 0, text=text,
                                         fill=self._fg_n, tags='text')
        self._redraw()

    def _redraw(self, event=None):
        self.delete('bg')
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 2 or h < 2:
            return

        if self._state == 'disabled':
            bg, fg = self._bg_d, self._fg_d
        elif self._state == 'pressed':
            bg, fg = self._bg_p, self._fg_p
        elif self._state == 'active':
            bg, fg = self._bg_a, self._fg_a
        else:
            bg, fg = self._bg_n, self._fg_n

        create_rounded_rect(self, 0, 0, w, h, self._cr,
                            fill=bg, outline='', tags='bg')
        self.coords(self._text_id, w / 2, h / 2)
        self.itemconfig(self._text_id, fill=fg)

    def _on_enter(self, _):
        if self._state == 'normal':
            self._state = 'active'
            self._redraw()

    def _on_leave(self, _):
        if self._state == 'active':
            self._state = 'normal'
            self._redraw()

    def _on_press(self, _):
        if self._state in ('normal', 'active'):
            self._state = 'pressed'
            self._redraw()

    def _on_release(self, event):
        if self._state == 'pressed':
            self._state = 'normal'
            self._redraw()
            # Check if click was within bounds
            x = self.winfo_pointerx() - self.winfo_rootx()
            y = self.winfo_pointery() - self.winfo_rooty()
            if (0 <= x <= self.winfo_width() and
                    0 <= y <= self.winfo_height() and self._command):
                self._command()

    def config_state(self, state: str):
        """Set button state: 'normal' or 'disabled'."""
        self._state = state if state == 'disabled' else 'normal'
        self._redraw()


class Card(tk.Frame):
    """A rounded card panel with dark background and optional title bar."""

    def __init__(self, master, title='', title_font=('', 10, 'bold'),
                 title_fg=ACCENT_BLUE, **kwargs):
        super().__init__(master, bg=CARD_BG, **kwargs)
        self._build(title, title_font, title_fg)

    def _build(self, title, title_font, title_fg):
        # Title
        if title:
            self.title_label = tk.Label(self, text=title, font=title_font,
                                        fg=title_fg, bg=CARD_BG, anchor='w')
            self.title_label.pack(fill='x', padx=14, pady=(12, 4))
        # Separator line
        sep = tk.Frame(self, height=1, bg=BORDER_COLOR)
        sep.pack(fill='x', padx=14, pady=(0, 8))
        # Content frame
        self.content = tk.Frame(self, bg=CARD_BG)
        self.content.pack(fill='both', expand=True, padx=14, pady=(0, 12))


class SidebarButton(tk.Canvas):
    """A sidebar tab item with active indicator (left bar) and hover."""

    SIDEBAR_W = 130
    ITEM_H = 38

    def __init__(self, master, text, icon='', command=None,
                 index=0, active=False):
        super().__init__(master, highlightthickness=0,
                         width=self.SIDEBAR_W, height=self.ITEM_H)
        self._command = command
        self._index = index
        self._active = active
        self._hover = False

        self._text = text
        self._icon = icon

        self.bind('<Enter>', lambda _: self._set_hover(True))
        self.bind('<Leave>', lambda _: self._set_hover(False))
        self.bind('<Button-1>', self._on_click)
        self.bind('<Configure>', lambda _: self._redraw())

        self._draw_bg()
        # Text label
        self._text_id = None
        self._init_labels()

    def _init_labels(self):
        # For simplicity we put a regular Label on top
        # (Canvas text doesn't handle font well across systems)
        self._label = tk.Label(self, text=self._text, anchor='w',
                               font=('', 10),
                               bg=SIDEBAR_BG, fg=TEXT_GRAY)
        self._label.place(x=36, y=0, width=self.SIDEBAR_W - 40,
                          height=self.ITEM_H)
        self._label.bind('<Button-1>', self._on_click)
        self._label.bind('<Enter>', lambda _: self._set_hover(True))
        self._label.bind('<Leave>', lambda _: self._set_hover(False))

        # Icon as small label
        self._icon_label = tk.Label(self, text=self._icon, anchor='center',
                                    font=('', 10),
                                    bg=SIDEBAR_BG, fg=TEXT_GRAY)
        self._icon_label.place(x=8, y=0, width=24, height=self.ITEM_H)
        self._icon_label.bind('<Button-1>', self._on_click)
        self._icon_label.bind('<Enter>', lambda _: self._set_hover(True))
        self._icon_label.bind('<Leave>', lambda _: self._set_hover(False))

    def _draw_bg(self):
        self.delete('bg')
        bg = SIDEBAR_BG
        if self._active:
            bg = ACCENT_BLUE
            fg = TEXT_WHITE
        elif self._hover:
            bg = HOVER_BG

        create_rounded_rect(self, 0, 0, self.SIDEBAR_W, self.ITEM_H,
                            4, fill=bg, outline='', tags='bg')

        # Active indicator: white left bar
        if self._active:
            self.create_rectangle(2, 6, 5, self.ITEM_H - 6,
                                  fill=TEXT_WHITE, outline='', tags='bg')

    def _redraw(self):
        self._draw_bg()
        if self._active:
            fg = TEXT_WHITE
        elif self._hover:
            fg = TEXT_WHITE
        else:
            fg = TEXT_GRAY

        self._label.config(fg=fg, bg=ACCENT_BLUE if self._active else
                           (HOVER_BG if self._hover else SIDEBAR_BG))
        self._icon_label.config(fg=fg, bg=ACCENT_BLUE if self._active else
                                (HOVER_BG if self._hover else SIDEBAR_BG))

    def _set_hover(self, on: bool):
        self._hover = on
        self._redraw()

    def _on_click(self, event=None):
        if self._command:
            self._command(self._index)

    def set_active(self, active: bool):
        self._active = active
        self._redraw()


def setup_dark_ttk_style():
    """Configure a dark ttk theme for all tab widgets.
    
    Call once in SettingsWindow._build_rich() so that ttk.Label, 
    ttk.Checkbutton, ttk.Combobox, etc. render with dark colors.
    """
    style = ttk.Style()
    style.theme_use('clam')  # 'clam' allows custom colors
    
    # Configure root dark colors
    style.configure('.', background=CARD_BG, foreground=TEXT_WHITE,
                    fieldbackground=INPUT_BG, selectbackground=ACCENT_BLUE,
                    selectforeground=TEXT_WHITE,
                    borderwidth=0, focuscolor='none')
    
    # Frame
    style.configure('TFrame', background=CARD_BG)
    style.configure('TLabelframe', background=CARD_BG, foreground=TEXT_WHITE)
    style.configure('TLabelframe.Label', background=CARD_BG, foreground=TEXT_WHITE)
    
    # Labels
    style.configure('TLabel', background=CARD_BG, foreground=TEXT_WHITE)
    
    # Buttons
    style.configure('TButton', background=BTN_SECONDARY, foreground=TEXT_WHITE,
                    borderwidth=0, focusthickness=3, focuscolor='none')
    style.map('TButton', background=[('active', ACCENT_BLUE)],
              foreground=[('active', TEXT_WHITE)])
    
    # Checkbuttons
    style.configure('TCheckbutton', background=CARD_BG, foreground=TEXT_WHITE,
                    focuscolor='none')
    style.map('TCheckbutton', background=[('active', CARD_BG)],
              foreground=[('active', TEXT_WHITE)])
    
    # Radiobuttons
    style.configure('TRadiobutton', background=CARD_BG, foreground=TEXT_WHITE,
                    focuscolor='none')
    
    # Combobox
    style.configure('TCombobox', fieldbackground=INPUT_BG, background=CARD_BG,
                    foreground=TEXT_WHITE, arrowcolor=TEXT_WHITE)
    style.map('TCombobox', fieldbackground=[('readonly', INPUT_BG)],
              background=[('readonly', CARD_BG)])
    
    # Entry
    style.configure('TEntry', fieldbackground=INPUT_BG, foreground=TEXT_WHITE,
                    insertcolor=TEXT_WHITE)
    
    # Separator
    style.configure('TSeparator', background=BORDER_COLOR)
    
    # Scrollbar
    style.configure('Vertical.TScrollbar', background=CARD_BG,
                    troughcolor=BG_DARK, arrowcolor=TEXT_GRAY)
    style.configure('Horizontal.TScrollbar', background=CARD_BG,
                    troughcolor=BG_DARK, arrowcolor=TEXT_GRAY)
    
    # Treeview
    style.configure('Treeview', background=INPUT_BG, foreground=TEXT_WHITE,
                    fieldbackground=INPUT_BG)
    style.configure('Treeview.Heading', background=BTN_SECONDARY,
                    foreground=TEXT_WHITE, font=('', 9, 'bold'))
    style.map('Treeview', background=[('selected', ACCENT_BLUE)],
              foreground=[('selected', TEXT_WHITE)])
    
    # Sizegrip (bottom-right resize handle)
    style.configure('TSizegrip', background=BG_DARK)
