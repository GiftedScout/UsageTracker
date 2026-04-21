"""
通知模块
- PowerShell Toast 通知（唯一通知方式，移除 plyer）
- 满 60 分钟首次提醒，之后每 30 分钟再次提醒
"""

import logging
import subprocess
import threading
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, Optional

from .i18n import t

logger = logging.getLogger(__name__)


@dataclass
class AppAlertState:
    """应用提醒状态"""
    category: str
    total_seconds: float = 0.0
    first_alert_sent: bool = False
    last_alert_time: Optional[datetime] = None
    alert_count: int = 0


class UsageNotifier:
    """使用时长提醒器"""

    FIRST_ALERT_THRESHOLD = 3600      # 1小时
    SUBSEQUENT_ALERT_INTERVAL = 1800  # 30分钟

    def __init__(self):
        self.alert_states: Dict[str, AppAlertState] = {}
        self._lock = threading.Lock()

    def update_usage(self, category: str, duration_seconds: float) -> list[str]:
        """更新使用时长并检查是否需要提醒，返回触发的消息列表"""
        alerts: list[str] = []
        with self._lock:
            if category not in ('browser', 'game'):
                return alerts
            if category not in self.alert_states:
                self.alert_states[category] = AppAlertState(category=category)
            state = self.alert_states[category]
            state.total_seconds = duration_seconds
            if duration_seconds < self.FIRST_ALERT_THRESHOLD:
                return alerts
            expected_count = 1 + int(
                (duration_seconds - self.FIRST_ALERT_THRESHOLD) / self.SUBSEQUENT_ALERT_INTERVAL)
            if state.alert_count < expected_count:
                is_first = (state.alert_count == 0)
                msg = self._create_alert_message(category, duration_seconds, is_first)
                alerts.append(msg)
                state.first_alert_sent = True
                state.alert_count = expected_count
                state.last_alert_time = datetime.now()
        for alert in alerts:
            self._send_notification(category, alert)
        return alerts

    def _create_alert_message(self, category: str, duration_seconds: float, is_first: bool) -> str:
        duration_minutes = int(duration_seconds / 60)
        cat_name = t(f'notifier.{category}', category)
        if is_first:
            return t('notifier.first_alert', cat=cat_name, minutes=duration_minutes)
        extra = duration_minutes - 60
        return t('notifier.repeat_alert', cat=cat_name, minutes=duration_minutes, extra=extra)

    def _send_notification(self, category: str, message: str) -> None:
        title = t('notifier.title')
        if not self._send_powershell_toast(title, message):
            logger.warning('Toast 通知发送失败')

    @staticmethod
    def _xml_escape(s: str) -> str:
        return (s.replace('&', '&amp;').replace('<', '&lt;')
                .replace('>', '&gt;').replace('"', '&quot;').replace("'", '&apos;'))

    def _send_powershell_toast(self, title: str, message: str) -> bool:
        t = self._xml_escape(title)
        m = self._xml_escape(message)
        app_id = r'{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'
        ps_script = (
            "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null\n"
            "[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null\n"
            "$xml = New-Object Windows.Data.Xml.Dom.XmlDocument\n"
            f"$xml.LoadXml('<toast><visual><binding template=\"ToastGeneric\"><text>{t}</text><text>{m}</text></binding></visual></toast>')\n"
            "$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)\n"
            f"[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{app_id}').Show($toast)\n"
        )
        try:
            result = subprocess.run(
                ['powershell', '-NoProfile', '-NonInteractive', '-WindowStyle', 'Hidden',
                 '-Command', ps_script],
                capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                logger.warning('Toast 失败 (rc=%d): %s', result.returncode, result.stderr[:150])
            return result.returncode == 0
        except Exception as e:
            logger.warning('Toast 异常: %s', e)
            return False

    def reset_category(self, category: str) -> None:
        with self._lock:
            self.alert_states.pop(category, None)

    def reset_all(self) -> None:
        with self._lock:
            self.alert_states.clear()

    def get_alert_summary(self) -> Dict:
        with self._lock:
            return {
                cat: {
                    'total_minutes': round(s.total_seconds / 60, 1),
                    'alert_count': s.alert_count,
                    'first_alert_sent': s.first_alert_sent,
                }
                for cat, s in self.alert_states.items()
            }
