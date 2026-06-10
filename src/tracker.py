"""
Windows 前台应用使用时长追踪器
支持事件驱动（SetWinEventHook）+ 轮询降级双模式
"""

import ctypes
import ctypes.wintypes
import logging
import threading
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Callable, Dict

import psutil

from .platform_utils import IS_WINDOWS, get_foreground_window_info

logger = logging.getLogger(__name__)

EVENT_SYSTEM_FOREGROUND = 0x0003
WINEVENT_OUTOFCONTEXT = 0x0002
_FALLBACK_THRESHOLD = 3  # 连续 3 次事件丢失降级轮询


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
    """使用时长追踪器（事件驱动+轮询降级）"""

    def __init__(self, check_interval: int = 5,
                 detection_mode: str = 'auto',
                 max_sessions: int = 1000):
        """
        max_sessions: 内存中保留的已结束 session 上限（循环缓冲区）
        """
        self.check_interval = check_interval
        self._detection_mode = detection_mode
        self._actual_mode = detection_mode
        self._max_sessions = max_sessions  # 实际运行模式（auto 可能降级）

        self.is_running = False
        self.current_session: Optional[AppSession] = None
        self.sessions: list[AppSession] = []
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._event_thread: Optional[threading.Thread] = None

        self.on_app_switch: Optional[
            Callable[[Optional[AppSession], Optional[AppSession]], None]] = None
        self.on_minimize_change: Optional[
            Callable[[Optional[AppSession], bool], None]] = None

        self._load_winapi()

        # 事件驱动状态
        self._event_hook_handle = None
        self._event_proc = None  # keep ref to prevent GC
        self._event_miss_count = 0
        self._last_event_time = 0.0
        self._hook_ready = threading.Event()
        self._ms_loop_running = threading.Event()

        # 共享的最新前台窗口
        self._latest_hwnd = None
        self._lock = threading.Lock()

    def _load_winapi(self) -> None:
        if not IS_WINDOWS:
            self.user32 = None
            return
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

    # ── 事件驱动钩子 ────────────────────────────────────────

    def _get_window_info(self) -> Optional[Dict]:
        """Get info for current foreground window (Win32 or platform fallback)."""
        if not IS_WINDOWS:
            return get_foreground_window_info()
        try:
            hwnd = self.user32.GetForegroundWindow()
            return self._build_window_info(hwnd)
        except Exception as e:
            logger.warning('获取窗口信息失败: %s', e)
            return None

    def _build_window_info(self, hwnd) -> Optional[Dict]:
        if not IS_WINDOWS:
            return None
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

    def _event_callback(self, hWinEventHook, event, hwnd,
                        idObject, idChild, dwEventThread, dwmsEventTime):
        """回调：前台窗口切换时触发"""
        if self._stop_event.is_set():
            return
        with self._lock:
            self._last_event_time = dwmsEventTime
            self._event_miss_count = 0  # 重置丢失计数
        self._on_foreground_change(hwnd)

    def _on_foreground_change(self, hwnd):
        """处理前台窗口切换（事件/轮询共用）"""
        if not hwnd:
            return
        window_info = self._build_window_info(hwnd)
        if not window_info:
            return
        window_key = window_info['name'].lower()
        is_minimized = window_info['is_minimized']

        if is_minimized:
            if self.current_session:
                self._end_current_session()
            return

        if self.current_session and self.current_session.name.lower() == window_key:
            self._update_current_duration()
            return

        # 切换到新窗口
        if self.current_session:
            self._end_current_session()
            if self.on_app_switch:
                old = self.sessions[-1] if self.sessions else None
                self.on_app_switch(old, None)

        self.current_session = AppSession(
            name=window_info['name'],
            exe_path=window_info['exe_path'],
            window_title=window_info['window_title'],
            start_time=datetime.now(),
        )
        if self.on_app_switch:
            old = self.sessions[-2] if len(self.sessions) >= 1 else None
            self.on_app_switch(old, self.current_session)

    def _setup_event_hook(self) -> bool:
        """注册 SetWinEventHook 事件钩子"""
        try:
            WinEventProc = ctypes.WINFUNCTYPE(
                None, ctypes.wintypes.HANDLE, ctypes.wintypes.DWORD,
                ctypes.wintypes.HWND, ctypes.wintypes.LONG,
                ctypes.wintypes.LONG, ctypes.wintypes.DWORD, ctypes.wintypes.DWORD
            )
            self._event_proc = WinEventProc(self._event_callback)
            hook = self.user32.SetWinEventHook(
                EVENT_SYSTEM_FOREGROUND, EVENT_SYSTEM_FOREGROUND,
                0, self._event_proc, 0, 0, WINEVENT_OUTOFCONTEXT)
            if not hook:
                logger.warning('SetWinEventHook 失败，回退轮询')
                return False
            self._event_hook_handle = hook
            logger.info('事件驱动钩子注册成功')
            return True
        except Exception as e:
            logger.warning('注册事件钩子异常: %s', e)
            return False

    def _unhook_event(self):
        """取消事件钩子"""
        if self._event_hook_handle:
            try:
                self.user32.UnhookWinEvent(self._event_hook_handle)
            except Exception:
                pass
            self._event_hook_handle = None
            self._event_proc = None

    def _event_message_loop(self):
        """事件驱动的消息循环线程（WinEventHook 需要）"""
        if not self._setup_event_hook():
            self._hook_ready.set()
            self._on_hook_failed()
            return
        self._hook_ready.set()
        # 初始化前台状态
        hwnd = self.user32.GetForegroundWindow()
        if hwnd:
            self._on_foreground_change(hwnd)

        msg = ctypes.wintypes.MSG()
        while not self._stop_event.is_set():
            ret = self.user32.GetMessageW(ctypes.byref(msg), 0, 0, 0)
            if ret <= 0:  # WM_QUIT or error
                break
            self.user32.TranslateMessage(msg)
            self.user32.DispatchMessageW(msg)

    def _on_hook_failed(self):
        """事件钩子失败时强制切换为轮询"""
        if self._detection_mode == 'event':
            logger.error('事件驱动钩子失败，但配置强制 event，继续尝试')
        else:
            logger.info('事件驱动不可用，降级到轮询模式')
            self._actual_mode = 'polling'

    def _monitor_event_health(self):
        """监控事件驱动健康，连续丢失降级轮询"""
        if self._detection_mode == 'polling':
            return
        import time as _time
        last_check = _time.time()
        while not self._stop_event.is_set():
            self._stop_event.wait(3)
            if self._actual_mode == 'polling':
                break
            if self._stop_event.is_set():
                break
            now = _time.time()
            with self._lock:
                if self._last_event_time < (now - 15):  # 15s 无事件
                    self._event_miss_count += 1
                else:
                    self._event_miss_count = 0
                if self._event_miss_count >= _FALLBACK_THRESHOLD and \
                        self._detection_mode == 'auto':
                    logger.warning('连续 %d 次事件丢失，降级到轮询',
                                   _FALLBACK_THRESHOLD)
                    self._actual_mode = 'polling'
                    self._unhook_event()
                    break

    # ── 轮询（原逻辑） ─────────────────────────────────────

    def _polling_loop(self):
        """轮询追踪循环（原 5 秒模式，降级备用）"""
        last_window_key = None
        while not self._stop_event.is_set():
            try:
                window_info = self._get_window_info()
                if window_info:
                    self._on_polling_tick(window_info, last_window_key)
                    last_window_key = window_info['name'].lower()
                else:
                    if self.current_session:
                        self._end_current_session()
                        last_window_key = None
            except Exception as e:
                logger.error('轮询循环错误: %s', e, exc_info=True)
            except BaseException:
                logger.critical('轮询循环致命异常', exc_info=True)
                raise
            self._stop_event.wait(self.check_interval)

    def _on_polling_tick(self, window_info, last_key):
        window_key = window_info['name'].lower()
        is_minimized = window_info['is_minimized']
        if window_key != last_key:
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
        elif self.current_session:
            if is_minimized != self.current_session.is_minimized:
                if is_minimized:
                    self._end_current_session()
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

    # ── 通用 ───────────────────────────────────────────

    def _update_current_duration(self) -> None:
        if self.current_session:
            self.current_session.duration_seconds = (
                datetime.now() - self.current_session.start_time).total_seconds()

    def _end_current_session(self) -> None:
        if self.current_session:
            self._update_current_duration()
            self.current_session.end_time = datetime.now()
            self.sessions.append(self.current_session)
            # 循环缓冲区：超出上限时丢弃最旧的一半
            if len(self.sessions) > self._max_sessions:
                self.sessions = self.sessions[-self._max_sessions // 2:]
            self.current_session = None

    def start(self) -> None:
        if self.is_running:
            return
        self.is_running = True
        self._stop_event.clear()

        # Linux/other Phase1：统一轮询平台封装，避免触碰 Win32 API。
        mode = self._detection_mode
        if not IS_WINDOWS:
            if mode == 'event':
                logger.warning('非 Windows 暂不支持事件驱动，降级为轮询')
            logger.info('启动平台轮询追踪（check_interval=%ds）', self.check_interval)
            self._actual_mode = 'polling'
            self._thread = threading.Thread(target=self._polling_loop,
                                            daemon=True)
            self._thread.start()
            return

        # 确定模式
        if mode == 'polling':
            logger.info('启动轮询追踪（check_interval=%ds）', self.check_interval)
            self._actual_mode = 'polling'
            self._load_winapi()
            self._thread = threading.Thread(target=self._polling_loop,
                                            daemon=True)
            self._thread.start()
        else:
            # auto 或 event：先尝试事件驱动
            try:
                self._load_winapi()
                self._event_thread = threading.Thread(
                    target=self._event_message_loop, daemon=True,
                    name='win-event-hook')
                self._event_thread.start()
                # 等待事件循环 ready（最多 2 秒）
                if not self._hook_ready.wait(timeout=2):
                    raise RuntimeError('event hook not ready')
                self._actual_mode = 'event'
                logger.info('启动事件驱动追踪')
                self._health_thread = threading.Thread(
                    target=self._monitor_event_health, daemon=True,
                    name='event-health')
                self._health_thread.start()
                # 也启动一个心跳线程更新 duration（事件驱动只是切换检测，
                # 但 duration 更新需要持续计时）
                self._heartbeat_thread = threading.Thread(
                    target=self._heartbeat_loop, daemon=True,
                    name='heartbeat')
                self._heartbeat_thread.start()
                logger.info('事件驱动追踪已启动')
            except Exception as e:
                if mode == 'event':
                    logger.error('事件驱动启动失败，降级轮询: %s', e)
                else:
                    logger.warning('事件驱动不可用，自动降级轮询: %s', e)
                self._actual_mode = 'polling'
                self._thread = threading.Thread(target=self._polling_loop,
                                                daemon=True)
                self._thread.start()

    def _heartbeat_loop(self):
        """心跳：定期更新当前 session 的 duration 秒数"""
        while not self._stop_event.is_set():
            self._stop_event.wait(1.0)
            if self._stop_event.is_set():
                break
            with self._lock:
                self._update_current_duration()

    def stop(self) -> None:
        if not self.is_running:
            return
        self._stop_event.set()
        self.is_running = False

        # 发送 WM_QUIT 以退出事件消息循环
        if IS_WINDOWS and self._event_thread and self._event_thread.is_alive():
            try:
                ctypes.windll.user32.PostQuitMessage(0)
            except Exception:
                pass

        self._unhook_event()
        for t_name in ('_thread', '_event_thread', '_health_thread',
                       '_heartbeat_thread'):
            t = getattr(self, t_name, None)
            if t and t.is_alive():
                t.join(timeout=2)

        self._end_current_session()
        logger.info('使用时长追踪已停止')

    def get_today_sessions(self) -> list[AppSession]:
        today = datetime.now().date()
        return [s for s in self.sessions if s.start_time.date() == today]

    def get_app_usage_stats(self, sessions: list[AppSession] | None = None
                            ) -> Dict[str, float]:
        if sessions is None:
            sessions = self.get_today_sessions()
        stats: Dict[str, float] = {}
        for session in sessions:
            stats[session.name] = stats.get(session.name, 0.0) + session.duration_seconds
        return stats

    @property
    def detection_mode(self) -> str:
        """返回实际运行模式"""
        return self._actual_mode
