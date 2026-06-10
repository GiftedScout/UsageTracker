"""
开机启动管理。
- Windows：通过 VBS 创建 Startup 快捷方式。
- Linux：通过 XDG Autostart 写入 ~/.config/autostart/UsageTracker.desktop。
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from pathlib import Path

from .platform_utils import IS_LINUX, IS_WINDOWS, linux_desktop_entry_path, make_linux_desktop_entry

logger = logging.getLogger(__name__)


class StartupManager:
    """开机启动管理器"""

    def __init__(self, app_name: str = 'UsageTracker', exe_path: str | None = None):
        self.app_name = app_name
        self.exe_path = exe_path
        if IS_WINDOWS:
            appdata = os.environ.get('APPDATA', '')
            self.shortcut_dir = Path(appdata) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / 'Startup'
            self._shortcut_path = self.shortcut_dir / f'{self.app_name}.lnk'
        elif IS_LINUX:
            self.shortcut_dir = linux_desktop_entry_path(app_name).parent
            self._shortcut_path = linux_desktop_entry_path(app_name)
        else:
            self.shortcut_dir = Path.home()
            self._shortcut_path = self.shortcut_dir / f'.{self.app_name}.startup'

    @property
    def shortcut_path(self) -> Path:
        return self._shortcut_path

    def is_startup_enabled(self) -> bool:
        return self.shortcut_path.exists()

    def check_available(self) -> dict:
        """非破坏性检查开机自启是否可配置；不创建、不删除任何系统/用户文件。"""
        if IS_LINUX:
            path = self.shortcut_path
            return {
                'platform': 'linux',
                'available': True,
                'backend': 'xdg-autostart',
                'path': str(path),
                'directory_exists': path.parent.exists(),
                'enabled': path.exists(),
                'exe_path_valid': bool(self.exe_path and Path(self.exe_path).exists()),
            }
        if IS_WINDOWS:
            return {
                'platform': 'windows',
                'available': True,
                'backend': 'startup-shortcut',
                'path': str(self.shortcut_path),
                'directory_exists': self.shortcut_path.parent.exists(),
                'enabled': self.shortcut_path.exists(),
                'exe_path_valid': bool(self.exe_path and Path(self.exe_path).exists()),
            }
        return {
            'platform': 'unknown',
            'available': False,
            'backend': 'unsupported',
            'path': str(self.shortcut_path),
            'enabled': self.shortcut_path.exists(),
            'exe_path_valid': bool(self.exe_path and Path(self.exe_path).exists()),
        }

    def enable_startup(self) -> bool:
        if IS_LINUX:
            return self._enable_linux_startup()
        if IS_WINDOWS:
            return self._enable_windows_startup()
        logger.warning('当前平台暂不支持开机启动')
        return False

    def _enable_linux_startup(self) -> bool:
        """创建 XDG Autostart .desktop 文件。"""
        if not self.exe_path or not Path(self.exe_path).exists():
            logger.warning('启动路径无效，无法创建 autostart: %s', self.exe_path)
            return False
        try:
            self.shortcut_dir.mkdir(parents=True, exist_ok=True)
            self.shortcut_path.write_text(
                make_linux_desktop_entry(self.app_name, self.exe_path),
                encoding='utf-8'
            )
            try:
                self.shortcut_path.chmod(0o644)
            except Exception:
                pass
            logger.info('Linux 开机启动已启用: %s', self.shortcut_path)
            return True
        except Exception as e:
            logger.error('启用 Linux 开机启动失败: %s', e)
            return False

    def _enable_windows_startup(self) -> bool:
        """创建 Windows 开机启动快捷方式（通过 VBS 脚本，避免引号问题）。"""
        if not self.exe_path or not Path(self.exe_path).exists():
            logger.warning('exe 路径无效，无法创建启动快捷方式: %s', self.exe_path)
            return False
        try:
            target = str(Path(self.exe_path).resolve())
            working_dir = str(Path(self.exe_path).parent.resolve())
            shortcut = str(self.shortcut_path)
            self.shortcut_dir.mkdir(parents=True, exist_ok=True)
            vbs = (
                f'Set WshShell = CreateObject("WScript.Shell")\n'
                f'Set Shortcut = WshShell.CreateShortcut("{shortcut}")\n'
                f'Shortcut.TargetPath = "{target}"\n'
                f'Shortcut.WorkingDirectory = "{working_dir}"\n'
                f'Shortcut.Save\n'
            )
            with tempfile.NamedTemporaryFile(suffix='.vbs', delete=False, mode='w', encoding='utf-8') as f:
                f.write(vbs)
                vbs_path = f.name
            try:
                result = subprocess.run(
                    ['wscript', '//NoLogo', vbs_path],
                    capture_output=True, text=True, timeout=10)
                if result.returncode == 0 and self.shortcut_path.exists():
                    logger.info('开机启动已启用: %s', shortcut)
                    return True
                logger.warning('创建快捷方式失败: rc=%d stderr=%s', result.returncode, result.stderr)
                return False
            finally:
                try:
                    os.unlink(vbs_path)
                except Exception:
                    pass
        except Exception as e:
            logger.error('启用开机启动失败: %s', e)
            return False

    def disable_startup(self) -> bool:
        """移除开机启动项。"""
        try:
            if self.shortcut_path.exists():
                self.shortcut_path.unlink()
                logger.info('开机启动已禁用')
                return True
            return False
        except Exception as e:
            logger.error('禁用开机启动失败: %s', e)
            return False
