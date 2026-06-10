"""
跨平台系统能力封装。

Windows 版最初直接调用 Win32 API；Linux Phase1 目标是在 GNOME Wayland 下先可运行：
- XWayland/X11 窗口：通过 xprop 读取 _NET_ACTIVE_WINDOW / WM_PID / WM_NAME。
- 原生 Wayland 窗口：GNOME Shell 未授予 Introspect 权限时不可枚举，返回 None 并让追踪器结束当前会话。
- 通知：Linux 使用 notify-send；Windows 仍走原 Toast/MessageBox。
- 自启：Linux 使用 XDG autostart .desktop；Windows 由 startup_manager 继续处理。
"""

from __future__ import annotations

import logging
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)

IS_WINDOWS = sys.platform.startswith('win')
IS_LINUX = sys.platform.startswith('linux')
if IS_LINUX:
    import fcntl
IS_MACOS = sys.platform == 'darwin'


def is_windows() -> bool:
    return IS_WINDOWS


def is_linux() -> bool:
    return IS_LINUX


def desktop_session() -> str:
    return (os.environ.get('XDG_SESSION_TYPE') or '').lower()


def desktop_name() -> str:
    return (os.environ.get('XDG_CURRENT_DESKTOP') or os.environ.get('DESKTOP_SESSION') or '').lower()


def _run_text(cmd: list[str], timeout: float = 1.5) -> str:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, errors='replace')
        if p.returncode != 0:
            return ''
        return (p.stdout or '').strip()
    except Exception:
        return ''


def _linux_proc_name(pid: int) -> str:
    if pid <= 0:
        return 'Unknown'
    for candidate in (Path('/proc') / str(pid) / 'comm',):
        try:
            txt = candidate.read_text(encoding='utf-8', errors='replace').strip()
            if txt:
                return txt
        except Exception:
            pass
    try:
        cmdline = (Path('/proc') / str(pid) / 'cmdline').read_text(encoding='utf-8', errors='replace')
        if cmdline:
            return Path(cmdline.split('\0')[0]).name or 'Unknown'
    except Exception:
        pass
    return 'Unknown'


def _linux_proc_exe(pid: int) -> str:
    if pid <= 0:
        return ''
    try:
        return str((Path('/proc') / str(pid) / 'exe').resolve())
    except Exception:
        return ''


def _parse_xprop_value(output: str) -> str:
    if '=' not in output:
        return ''
    value = output.split('=', 1)[1].strip()
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    return value


def get_linux_foreground_window() -> Optional[Dict]:
    """返回 XWayland/X11 活动窗口信息；Wayland 原生窗口不可见时返回 None。"""
    if not shutil.which('xprop'):
        logger.debug('xprop 不存在，无法读取 X11/XWayland 前台窗口')
        return None

    active = _run_text(['xprop', '-root', '_NET_ACTIVE_WINDOW'])
    if not active or 'window id #' not in active:
        return None
    win_id = active.rsplit('#', 1)[-1].strip().split()[0]
    if not win_id or win_id in {'0x0', '0x0000000'}:
        return None

    pid_text = _run_text(['xprop', '-id', win_id, '_NET_WM_PID'])
    pid = 0
    m = None
    try:
        import re
        m = re.search(r'=\s*(\d+)', pid_text or '')
    except Exception:
        m = None
    if m:
        try:
            pid = int(m.group(1))
        except Exception:
            pid = 0

    title = ''
    for prop in ('_NET_WM_NAME', 'WM_NAME'):
        val = _run_text(['xprop', '-id', win_id, prop])
        if val and '=' in val:
            title = _parse_xprop_value(val)
            if title:
                break

    name = _linux_proc_name(pid)
    exe_path = _linux_proc_exe(pid)
    if name == 'Unknown' and title:
        name = title

    return {
        'hwnd': win_id,
        'pid': pid,
        'name': name,
        'exe_path': exe_path,
        'window_title': title,
        'is_minimized': False,
        'is_visible': True,
        'backend': 'xprop',
    }


def get_foreground_window_info() -> Optional[Dict]:
    if IS_LINUX:
        return get_linux_foreground_window()
    return None


def show_message(title: str, text: str, style: int = 0x40) -> bool:
    """Best-effort 跨平台提示框/通知。"""
    if IS_WINDOWS:
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, text, title, style)
            return True
        except Exception as e:
            logger.warning('Windows MessageBox 失败: %s', e)
            return False
    if IS_LINUX:
        if shutil.which('notify-send'):
            try:
                subprocess.run(['notify-send', title, text], timeout=5)
                return True
            except Exception as e:
                logger.warning('notify-send 失败: %s', e)
        logger.info('%s: %s', title, text)
        return False
    logger.info('%s: %s', title, text)
    return False


def send_notification(title: str, message: str) -> bool:
    if IS_LINUX and shutil.which('notify-send'):
        try:
            result = subprocess.run(['notify-send', title, message], capture_output=True, timeout=5)
            if result.returncode != 0:
                logger.warning('notify-send 失败 rc=%s stderr=%s', result.returncode, (result.stderr or b'')[:150])
            return result.returncode == 0
        except Exception as e:
            logger.warning('notify-send 异常: %s', e)
            return False
    return show_message(title, message)


def open_path(path: str | os.PathLike[str]) -> bool:
    """用平台默认程序打开文件或目录。"""
    try:
        if IS_WINDOWS:
            os.startfile(str(path))  # type: ignore[attr-defined]
            return True
        opener = 'open' if IS_MACOS else 'xdg-open'
        if not shutil.which(opener):
            logger.warning('未找到打开路径的工具: %s', opener)
            return False
        subprocess.Popen([opener, str(path)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as exc:
        logger.warning('打开路径失败 %s: %s', path, exc)
        return False


class FileLockSingleInstance:
    """Linux/macOS 单实例：fcntl 文件锁，进程退出自动释放。"""

    def __init__(self, app_name: str = 'UsageTracker'):
        runtime = os.environ.get('XDG_RUNTIME_DIR')
        if runtime:
            lock_dir = Path(runtime)
        else:
            lock_dir = Path.home() / '.cache'
        lock_dir.mkdir(parents=True, exist_ok=True)
        self.lock_path = lock_dir / f'{app_name}.lock'
        # Do not open with 'w' here: a second process that fails to acquire the
        # lock would truncate the PID written by the running daemon, making
        # status/stop report "PID unknown".
        self._fh = open(self.lock_path, 'a+')
        try:
            fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._fh.seek(0)
            self._fh.truncate()
            self._fh.write(str(os.getpid()))
            self._fh.flush()
            self.already_running = False
        except BlockingIOError:
            self.already_running = True

    def release(self) -> None:
        try:
            fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass
        try:
            self._fh.close()
        except Exception:
            pass


def linux_autostart_dir() -> Path:
    return Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'autostart'


def linux_desktop_entry_path(app_name: str) -> Path:
    safe = ''.join(c if c.isalnum() or c in ('-', '_') else '-' for c in app_name)
    return linux_autostart_dir() / f'{safe}.desktop'


# ---- XDG Base Directory 辅助函数 ----

def linux_config_dir(app_name: str = 'usagetracker') -> Path:
    """~/.config/<app_name> 或 $XDG_CONFIG_HOME/<app_name>"""
    return Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / app_name


def linux_data_dir(app_name: str = 'usagetracker') -> Path:
    """~/.local/share/<app_name> 或 $XDG_DATA_HOME/<app_name>"""
    return Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share')) / app_name


def linux_state_dir(app_name: str = 'usagetracker') -> Path:
    """~/.local/state/<app_name> 或 $XDG_STATE_HOME/<app_name>"""
    return Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local' / 'state')) / app_name


def make_linux_desktop_entry(app_name: str, exe_path: str) -> str:
    target = Path(exe_path).resolve()
    workdir = target.parent
    # 如果是 .py，优先用当前解释器启动；否则直接启动可执行文件。
    if target.suffix == '.py':
        exec_line = f'{shlex_quote(sys.executable)} {shlex_quote(str(target))}'
    else:
        exec_line = shlex_quote(str(target))
    return '\n'.join([
        '[Desktop Entry]',
        'Type=Application',
        f'Name={app_name}',
        f'Exec={exec_line}',
        f'Path={workdir}',
        'Terminal=false',
        'X-GNOME-Autostart-enabled=true',
        '',
    ])


def shlex_quote(s: str) -> str:
    import shlex
    return shlex.quote(s)
