"""
Windows 前台应用使用时长追踪器
监测前台窗口，记录应用使用时长（最小化不计入）
"""

import ctypes
import ctypes.wintypes
import logging
import threading
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Callable, Dict

import psutil

logger = logging.getLogger(__name__)


@dataclass
class AppSession:
    """应用使用会话"""
    name: str
    exe_path: str
    window_title: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    is_minimized: bool = False


class UsageTracker:
    """使用时长追踪器"""

    def __init__(self, check_interval: int = 5):
        self.check_interval = check_interval
        self.is_running = False
        self.current_session: Optional[AppSession] = None
        self.sessions: list[AppSession] = []
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self.on_app_switch: Optional[Callable[[Optional[AppSession], Optional[AppSession]], None]] = None
        self.on_minimize_change: Optional[Callable[[Optional[AppSession], bool], None]] = None

        self._load_winapi()

    def _load_winapi(self) -> None:
        """加载 Windows API 函数"""
        self.user32 = ctypes.windll.user32
        self.user32.GetForegroundWindow.restype = ctypes.wintypes.HWND
        self.user32.GetWindowThreadProcessId.argtypes = [
            ctypes.wintypes.HWND, ctypes.POINTER(ctypes.wintypes.DWORD)]
        self.user32.GetWindowThreadProcessId.restype = ctypes.wintypes.DWORD
        self.user32.IsIconic.argtypes = [ctypes.wintypes.HWND]
        self.user32.IsIconic.restype = ctypes.wintypes.BOOL
        self.user32.IsWindowVisible.argtypes = [ctypes.wintypes.HWND]
        self.user32.IsWindowVisible.restype = ctypes.wintypes.BOOL
        self.user32.GetWindowTextW.argtypes = [
            ctypes.wintypes.HWND, ctypes.wintypes.LPWSTR, ctypes.c_int]
        self.user32.GetWindowTextW.restype = ctypes.c_int

    def get_foreground_window_info(self) -> Optional[Dict]:
        """获取当前前台窗口信息"""
        try:
            hwnd = self.user32.GetForegroundWindow()
            if not hwnd:
                return None
            pid = ctypes.wintypes.DWORD()
            self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            title_buffer = ctypes.create_unicode_buffer(1024)
            self.user32.GetWindowTextW(hwnd, title_buffer, 1024)
            try:
                process = psutil.Process(pid.value)
                exe_path = process.exe()
                name = process.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                exe_path = ''
                name = 'Unknown'
            return {
                'hwnd': hwnd, 'pid': pid.value, 'name': name,
                'exe_path': exe_path, 'window_title': title_buffer.value,
                'is_minimized': bool(self.user32.IsIconic(hwnd)),
                'is_visible': bool(self.user32.IsWindowVisible(hwnd)),
            }
        except Exception as e:
            logger.warning('获取窗口信息失败: %s', e)
            return None

    def _tracking_loop(self) -> None:
        """追踪主循环"""
        last_window_key = None
        while not self._stop_event.is_set():
            try:
                window_info = self.get_foreground_window_info()
                if window_info:
                    window_key = window_info['name'].lower()
                    is_minimized = window_info['is_minimized']
                    if window_key != last_window_key:
                        if self.current_session:
                            self._end_current_session()
                        if not is_minimized:
                            self.current_session = AppSession(
                                name=window_info['name'],
                                exe_path=window_info['exe_path'],
                                window_title=window_info['window_title'],
                                start_time=datetime.now(),
                            )
                            if self.on_app_switch:
                                self.on_app_switch(
                                    self.sessions[-1] if self.sessions else None,
                                    self.current_session)
                        last_window_key = window_key
                    elif self.current_session:
                        if is_minimized != self.current_session.is_minimized:
                            if is_minimized:
                                self._end_current_session()
                                last_window_key = None
                            else:
                                self.current_session = AppSession(
                                    name=window_info['name'],
                                    exe_path=window_info['exe_path'],
                                    window_title=window_info['window_title'],
                                    start_time=datetime.now(),
                                )
                            if self.on_minimize_change:
                                self.on_minimize_change(self.current_session, is_minimized)
                        else:
                            self._update_current_duration()
                else:
                    if self.current_session:
                        self._end_current_session()
                        last_window_key = None
            except Exception as e:
                logger.error('追踪循环错误: %s', e, exc_info=True)
            except BaseException:
                logger.critical('追踪循环致命异常', exc_info=True)
                raise
            self._stop_event.wait(self.check_interval)

    def _update_current_duration(self) -> None:
        if self.current_session:
            self.current_session.duration_seconds = (
                datetime.now() - self.current_session.start_time).total_seconds()

    def _end_current_session(self) -> None:
        if self.current_session:
            self._update_current_duration()
            self.current_session.end_time = datetime.now()
            self.sessions.append(self.current_session)
            self.current_session = None

    def start(self) -> None:
        if self.is_running:
            return
        self.is_running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self._thread.start()
        logger.info('使用时长追踪已启动')

    def stop(self) -> None:
        if not self.is_running:
            return
        self._stop_event.set()
        self.is_running = False
        if self._thread:
            self._thread.join(timeout=2)
        self._end_current_session()
        logger.info('使用时长追踪已停止')

    def get_today_sessions(self) -> list[AppSession]:
        today = datetime.now().date()
        return [s for s in self.sessions if s.start_time.date() == today]

    def get_app_usage_stats(self, sessions: list[AppSession] | None = None) -> Dict[str, float]:
        if sessions is None:
            sessions = self.get_today_sessions()
        stats: Dict[str, float] = {}
        for session in sessions:
            stats[session.name] = stats.get(session.name, 0.0) + session.duration_seconds
        return stats
