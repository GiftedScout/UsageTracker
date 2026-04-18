"""
单实例保障
使用 Windows 命名 Mutex 防止多开
"""

import ctypes
import logging

logger = logging.getLogger(__name__)


class SingleInstance:
    """通过 Windows Mutex 实现单实例"""

    def __init__(self, mutex_name: str = 'Global\\UsageTracker_SingleInstance'):
        self.mutex_name = mutex_name
        self.mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
        self.already_running = ctypes.windll.kernel32.GetLastError() == 183  # ERROR_ALREADY_EXISTS
        if self.already_running:
            logger.info('检测到已有实例运行')

    def __del__(self):
        if self.mutex:
            try:
                ctypes.windll.kernel32.ReleaseMutex(self.mutex)
                ctypes.windll.kernel32.CloseHandle(self.mutex)
            except Exception:
                pass
