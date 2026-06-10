"""
单实例保障：Windows 使用命名 Mutex；Linux/macOS 使用 fcntl 文件锁。
"""

from __future__ import annotations

import logging

from .platform_utils import IS_WINDOWS, FileLockSingleInstance

logger = logging.getLogger(__name__)


class SingleInstance:
    """跨平台单实例保护。"""

    def __init__(self, mutex_name: str = 'Global\\UsageTracker_SingleInstance'):
        self.mutex_name = mutex_name
        self.mutex = None
        self._file_lock = None
        if IS_WINDOWS:
            try:
                import ctypes
                self.mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
                self.already_running = ctypes.windll.kernel32.GetLastError() == 183  # ERROR_ALREADY_EXISTS
            except Exception as e:
                logger.warning('Windows Mutex 创建失败，降级为未检测多开: %s', e)
                self.already_running = False
        else:
            self._file_lock = FileLockSingleInstance('UsageTracker')
            self.already_running = self._file_lock.already_running
        if self.already_running:
            logger.info('检测到已有实例运行')

    def __del__(self):
        if self._file_lock:
            self._file_lock.release()
        if self.mutex:
            try:
                import ctypes
                ctypes.windll.kernel32.ReleaseMutex(self.mutex)
                ctypes.windll.kernel32.CloseHandle(self.mutex)
            except Exception:
                pass
