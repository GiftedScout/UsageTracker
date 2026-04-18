"""
崩溃恢复包装器
- 检测主进程异常退出（非 exit code 0）
- 通过 PowerShell Toast 通知用户后自动重启
- 最多重试 3 次
- 崩溃 traceback 写入 crash_logs 目录
"""

import logging
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


class CrashHandler:
    """崩溃恢复管理"""

    def __init__(self, retry_count_file: str | None = None):
        if retry_count_file is None:
            from .constants import DATA_DIR, CRASH_LOG_DIR
            self.retry_count_file = str(DATA_DIR / 'crash_retry_count')
            self.crash_log_dir = CRASH_LOG_DIR
        else:
            self.retry_count_file = retry_count_file
            self.crash_log_dir = Path(retry_count_file).parent / 'crash_logs'
        self.crash_log_dir.mkdir(parents=True, exist_ok=True)

    def wrap(self, target_func):
        """包装主进程入口，异常退出时自动重启"""
        while True:
            try:
                sys.exit(target_func())
            except SystemExit as e:
                if e.code == 0 or e.code is None:
                    break
                self._write_crash_log(f'非零退出码: {e.code}')
                retry = self._get_retry_count()
                if retry >= MAX_RETRIES:
                    self._notify_user('UsageTracker 连续崩溃，已停止重试')
                    break
                self._increment_retry_count()
                self._notify_user(f'UsageTracker 异常退出，正在重启 ({retry + 1}/{MAX_RETRIES})')
            except Exception:
                self._write_crash_log(traceback.format_exc())
                retry = self._get_retry_count()
                if retry >= MAX_RETRIES:
                    self._notify_user('UsageTracker 连续崩溃，已停止重试')
                    break
                self._increment_retry_count()
                self._notify_user(f'UsageTracker 异常退出，正在重启 ({retry + 1}/{MAX_RETRIES})')
        self._clear_retry_count()

    def _write_crash_log(self, error_text: str) -> None:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = self.crash_log_dir / f'crash_{ts}.log'
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f'时间: {datetime.now().isoformat()}\n')
                f.write(f'版本: {self._get_version()}\n')
                f.write(f'Python: {sys.version}\n')
                f.write(f'\n{error_text}\n')
            logger.error('崩溃日志已写入: %s', log_file)
        except Exception as e:
            logger.error('写入崩溃日志失败: %s', e)

    @staticmethod
    def _get_version() -> str:
        try:
            from .version import VERSION
            return VERSION
        except Exception:
            return 'unknown'

    def _get_retry_count(self) -> int:
        try:
            if os.path.exists(self.retry_count_file):
                with open(self.retry_count_file, 'r') as f:
                    return int(f.read().strip())
        except Exception:
            pass
        return 0

    def _increment_retry_count(self) -> None:
        count = self._get_retry_count() + 1
        try:
            with open(self.retry_count_file, 'w') as f:
                f.write(str(count))
        except Exception:
            pass

    def _clear_retry_count(self) -> None:
        try:
            if os.path.exists(self.retry_count_file):
                os.remove(self.retry_count_file)
        except Exception:
            pass

    def _notify_user(self, message: str) -> None:
        """通过 PowerShell Toast 通知用户"""
        import subprocess
        t = message.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        app_id = r'{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'
        ps = (
            "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null\n"
            "[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null\n"
            "$xml = New-Object Windows.Data.Xml.Dom.XmlDocument\n"
            f"$xml.LoadXml('<toast><visual><binding template=\"ToastGeneric\"><text>UsageTracker</text><text>{t}</text></binding></visual></toast>')\n"
            "$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)\n"
            f"[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{app_id}').Show($toast)\n"
        )
        try:
            subprocess.run(
                ['powershell', '-NoProfile', '-NonInteractive', '-WindowStyle', 'Hidden', '-Command', ps],
                capture_output=True, timeout=10)
        except Exception:
            pass

    @staticmethod
    def get_crash_logs(log_dir: str | Path | None = None) -> list[dict]:
        """获取所有崩溃日志列表"""
        if log_dir is None:
            from .constants import CRASH_LOG_DIR
            log_dir = CRASH_LOG_DIR
        logs = []
        log_path = Path(log_dir)
        if not log_path.exists():
            return logs
        for f in sorted(log_path.glob('crash_*.log'), reverse=True):
            try:
                stat = f.stat()
                logs.append({
                    'filename': f.name,
                    'path': str(f),
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
            except Exception:
                pass
        return logs
