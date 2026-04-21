"""
系统托盘应用
- pystray 托盘图标和右键菜单
- 左键打开设置，双击打开日报
- Tooltip 每 30 秒刷新
"""

import logging
import threading
from datetime import date, timedelta
from typing import Callable

from PIL import Image
import pystray

from .version import VERSION, APP_NAME
from .constants import TOOLTIP_UPDATE_INTERVAL
from .i18n import t

logger = logging.getLogger(__name__)


class TrayApp:
    """系统托盘应用"""

    def __init__(self, icon_image: Image.Image, data_store=None,
                 config_manager=None, report_generator=None,
                 on_settings=None, on_quit=None):
        self._data_store = data_store
        self._config = config_manager
        self._report_gen = report_generator
        self._on_settings = on_settings
        self._on_quit = on_quit
        self._stop_event = threading.Event()
        self._tooltip_thread: threading.Thread | None = None

        self.icon = pystray.Icon(
            name=APP_NAME,
            icon=icon_image,
            title=APP_NAME,
            menu=pystray.Menu(
                pystray.MenuItem(t('tray.yesterday_report'), self._open_daily),
                pystray.MenuItem(t('tray.last_week_report'), self._open_weekly),
                pystray.MenuItem(t('tray.last_month_report'), self._open_monthly),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(t('tray.settings'), self._open_settings, default=True),
                pystray.MenuItem(f'{t("tray.about")} ({VERSION})', self._show_about, enabled=False),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(t('tray.exit'), self._quit),
            ),
            on_double_click=self._open_daily,
        )

    def _open_daily(self, icon=None, item=None) -> None:
        self._generate_and_open('daily')

    def _open_weekly(self, icon=None, item=None) -> None:
        self._generate_and_open('weekly')

    def _open_monthly(self, icon=None, item=None) -> None:
        self._generate_and_open('monthly')

    def _get_report_date(self) -> str:
        """确定日报日期：优先昨天，若昨天无数据则回溯到最近有数据的日期"""
        if not self._data_store:
            return (date.today() - timedelta(days=1)).isoformat()

        today = date.today()
        # 先查昨天
        yesterday = today - timedelta(days=1)
        report = self._data_store.get_daily_report(yesterday.isoformat())
        if report:
            return yesterday.isoformat()

        # 回溯最多 7 天，找最近有数据的日期
        for i in range(2, 8):
            d = today - timedelta(days=i)
            report = self._data_store.get_daily_report(d.isoformat())
            if report:
                return d.isoformat()

        # 全都没有，回退到昨天（会提示无数据）
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
                    logger.info('没有日报数据')
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
            logger.error('生成报告失败: %s', e)

    def _open_settings(self, icon=None, item=None) -> None:
        if self._on_settings:
            self._on_settings()

    def _show_about(self, icon=None, item=None) -> None:
        pass  # enabled=False，不可点击

    def _quit(self, icon=None, item=None) -> None:
        self._stop_event.set()
        self.icon.stop()
        if self._on_quit:
            self._on_quit()

    def _update_tooltip_loop(self) -> None:
        """定时更新托盘悬浮提示"""
        while not self._stop_event.is_set():
            try:
                if self._data_store:
                    report = self._data_store.get_daily_report(
                        (date.today() - timedelta(days=1)).isoformat())
                    if report:
                        from .data_store import DataStore
                        b = DataStore.format_duration(report.browser_seconds)
                        g = DataStore.format_duration(report.game_seconds)
                        self.icon.title = f'UsageTracker | {t("tray.tooltip_yesterday", browser=b, game=g)}'
                    else:
                        self.icon.title = f'{APP_NAME} | {t("tray.tooltip_no_data")}'
            except Exception as e:
                logger.debug('更新 tooltip 失败: %s', e)
            self._stop_event.wait(TOOLTIP_UPDATE_INTERVAL)

    def run(self) -> None:
        """启动托盘图标（阻塞）"""
        self._stop_event.clear()
        self._tooltip_thread = threading.Thread(target=self._update_tooltip_loop, daemon=True)
        self._tooltip_thread.start()
        self.icon.run()

    def _notify_no_data(self, message: str) -> None:
        """无报告数据时发送 Toast 通知"""
        import subprocess
        app_id = r'{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'
        ps = (
            "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null\n"
            "[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null\n"
            "$xml = New-Object Windows.Data.Xml.Dom.XmlDocument\n"
            f"$xml.LoadXml('<toast><visual><binding template=\"ToastGeneric\"><text>UsageTracker</text><text>{message}</text></binding></visual></toast>')\n"
            "$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)\n"
            f"[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{app_id}').Show($toast)\n"
        )
        try:
            subprocess.run(
                ['powershell', '-NoProfile', '-NonInteractive', '-WindowStyle', 'Hidden', '-Command', ps],
                capture_output=True, timeout=8)
        except Exception as e:
            logger.debug('无数据提示 Toast 失败: %s', e)

    def stop(self) -> None:
        self._stop_event.set()
        self.icon.stop()
