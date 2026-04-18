"""
开机启动管理（适配 exe 分发）
- 通过 VBS 脚本创建快捷方式（避免 PowerShell 引号转义问题）
- 支持 exe 模式和 python 模式
"""

import logging
import os
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class StartupManager:
    """开机启动管理器"""

    def __init__(self, app_name: str = 'UsageTracker', exe_path: str | None = None):
        self.app_name = app_name
        self.exe_path = exe_path
        import os as _os
        appdata = _os.environ.get('APPDATA', '')
        self.shortcut_dir = Path(appdata) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / 'Startup'

    @property
    def shortcut_path(self) -> Path:
        return self.shortcut_dir / f'{self.app_name}.lnk'

    def is_startup_enabled(self) -> bool:
        return self.shortcut_path.exists()

    def enable_startup(self) -> bool:
        """创建开机启动快捷方式（通过 VBS 脚本，避免引号问题）"""
        if not self.exe_path or not Path(self.exe_path).exists():
            logger.warning('exe 路径无效，无法创建启动快捷方式: %s', self.exe_path)
            return False
        try:
            target = str(Path(self.exe_path).resolve())
            working_dir = str(Path(self.exe_path).parent.resolve())
            shortcut = str(self.shortcut_path)
            # 用 VBS 创建快捷方式，避免 PowerShell 引号转义陷阱
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
        """移除开机启动快捷方式"""
        try:
            if self.shortcut_path.exists():
                self.shortcut_path.unlink()
                logger.info('开机启动已禁用')
                return True
            return False
        except Exception as e:
            logger.error('禁用开机启动失败: %s', e)
            return False
