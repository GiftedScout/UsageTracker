"""
系统托盘应用
- pystray 托盘图标和右键菜单
- 左键打开设置，双击打开日报
- Tooltip 每 30 秒刷新
- v0.3.0+ 已弃用 tkinter，全部改用 webbrowser / ctypes MessageBox
- Linux Phase1: pystray/Pillow 延迟导入，缺失时模块级不崩溃
"""

import logging
import threading
from datetime import date, timedelta
from typing import Callable

# 延迟导入：pystray/Pillow 仅在使用托盘时按需加载
# from PIL import Image    ← moved into __init__
# import pystray           ← moved into __init__

from .version import VERSION, APP_NAME, RELEASE_NOTES
from .i18n import t
from .platform_utils import show_message

logger = logging.getLogger(__name__)


def _message_box(title: str, text: str, style: int = 0x40) -> int:
    """跨平台提示（Windows MessageBox / Linux notify-send / 控制台日志）。"""
    return 1 if show_message(title, text, style) else 0


class TrayApp:
    """系统托盘应用"""

    def __init__(self, icon_image, data_store=None,
                 config_manager=None, report_generator=None,
                 on_settings=None, on_quit=None, exe_path: str = ''):
        # 延迟导入 pystray，确保模块级不崩溃
        import pystray

        self._data_store = data_store
        self._config = config_manager
        self._report_gen = report_generator
        self._on_settings = on_settings
        self._on_quit = on_quit
        self._exe_path = exe_path
        self._stop_event = threading.Event()
        self._auto_open_daily = False

        self.icon = pystray.Icon(
            name=APP_NAME,
            icon=icon_image,
            title=APP_NAME,
            menu=pystray.Menu(
                pystray.MenuItem(t('tray.yesterday_report'), self._open_daily),
                pystray.MenuItem(t('tray.last_week_report'), self._open_weekly),
                pystray.MenuItem(t('tray.last_month_report'), self._open_monthly),
                pystray.MenuItem(t('tray.custom_report'), self._open_custom),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(t('tray.settings'), self._open_settings, default=True),
                pystray.MenuItem(t('tray.check_update'), self._check_update),
                pystray.MenuItem(f"{t('tray.about')} ({VERSION})", self._show_about),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(t('tray.exit'), self._quit),
            ),
            on_double_click=self._open_daily,
        )

    def _open_daily(self, icon=None, item=None) -> None:
        self._update_tooltip()
        threading.Thread(target=self._generate_and_open, args=('daily',),
                         daemon=True, name='open-daily').start()

    def _open_weekly(self, icon=None, item=None) -> None:
        self._update_tooltip()
        threading.Thread(target=self._generate_and_open, args=('weekly',),
                         daemon=True, name='open-weekly').start()

    def _open_monthly(self, icon=None, item=None) -> None:
        self._update_tooltip()
        threading.Thread(target=self._generate_and_open, args=('monthly',),
                         daemon=True, name='open-monthly').start()

    def _open_custom(self, icon=None, item=None) -> None:
        self._update_tooltip()
        import webbrowser
        webbrowser.open('http://127.0.0.1:19234/settings')

    def _get_report_date(self) -> str:
        if not self._data_store:
            return (date.today() - timedelta(days=1)).isoformat()
        today = date.today()
        yesterday = today - timedelta(days=1)
        report = self._data_store.get_daily_report(yesterday.isoformat())
        if report:
            return yesterday.isoformat()
        for i in range(2, 8):
            d = today - timedelta(days=i)
            report = self._data_store.get_daily_report(d.isoformat())
            if report:
                return d.isoformat()
        return yesterday.isoformat()

    def _generate_and_open(self, report_type: str) -> None:
        if not self._data_store or not self._report_gen:
            return
        theme = self._config.theme if self._config else 'fairy_tale'
        try:
            if report_type == 'daily':
                report_date = self._get_report_date()
                report = self._data_store.get_daily_report(report_date)
                if report:
                    path = self._report_gen.generate_daily_report(report, theme)
                    self._report_gen.open_report(path)
                else:
                    logger.info('no daily data')
                    self._notify_no_data(t('tray.no_data'))
                return
            elif report_type == 'weekly':
                today = date.today()
                last_monday = today - timedelta(days=today.weekday() + 7)
                last_sunday = last_monday + timedelta(days=6)
                path = self._report_gen.generate_weekly_report(
                    last_monday.isoformat(), last_sunday.isoformat(), theme)
            elif report_type == 'monthly':
                today = date.today()
                prev = today.replace(day=1) - timedelta(days=1)
                path = self._report_gen.generate_monthly_report(prev.year, prev.month, theme)
            else:
                return
            self._report_gen.open_report(path)
        except Exception as e:
            logger.error('report gen fail: %s', e)

    def _open_settings(self, icon=None, item=None) -> None:
        logger.info('tray: open settings')
        import webbrowser
        try:
            webbrowser.open('http://127.0.0.1:19234/settings')
        except Exception as e:
            logger.error('open settings fail: %s', e)

    def _check_update(self, icon=None, item=None) -> None:
        from .updater import check_update_async
        from .version import VERSION as _VER

        def _on_result(info):
            if info:
                ver = info.get('version', '')
                msg = '发现新版本 ' + ver + '！\n\n点击确定前往 GitHub 下载页面。'
                _message_box('UsageTracker - 更新', msg, 0x40 | 0x1)
                import webbrowser
                webbrowser.open(info.get('url', 'https://github.com/GiftedScout/UsageTracker/releases'))
            else:
                _message_box('UsageTracker - 更新', '当前已是最新版本。', 0x40)

        threading.Thread(
            target=lambda: check_update_async(_VER, callback=_on_result, force=True),
            daemon=True, name='check-update'
        ).start()

    def _show_about(self, icon=None, item=None) -> None:
        import webbrowser
        webbrowser.open('https://github.com/GiftedScout/UsageTracker/releases')

    def _quit(self, icon=None, item=None) -> None:
        self._stop_event.set()
        self.icon.stop()
        if self._on_quit:
            self._on_quit()

    def _update_tooltip(self) -> None:
        try:
            if self._data_store:
                report = self._data_store.get_daily_report(
                    (date.today() - timedelta(days=1)).isoformat())
                if report:
                    from .data_store import DataStore
                    b = DataStore.format_duration(report.browser_seconds)
                    d = DataStore.format_duration(report.development_seconds)
                    self.icon.title = f"UsageTracker | {t('tray.tooltip_yesterday', browser=b, development=d)}"
                else:
                    self.icon.title = f"{APP_NAME} | {t('tray.tooltip_no_data')}"
        except Exception as e:
            logger.debug('tooltip update fail: %s', e)

    def run(self) -> None:
        self._stop_event.clear()
        self._update_tooltip()
        if self._auto_open_daily:
            def _auto_report():
                self._stop_event.wait(1)
                if not self._stop_event.is_set():
                    self._open_daily()
            threading.Thread(target=_auto_report, daemon=True, name='auto-report').start()
        self.icon.run()

    def _notify_no_data(self, message: str) -> None:
        _message_box('UsageTracker', message, 0x40)

    def stop(self) -> None:
        self._stop_event.set()
        self.icon.stop()
