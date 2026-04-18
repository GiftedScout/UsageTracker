"""
应用分类器（配置驱动）
- 动态扫描 Steam 游戏库
- 自动扫描米哈游游戏目录
- 识别浏览器类应用
- 支持自定义分类和忽略名单
"""

import json
import logging
import os
import re
import winreg
from pathlib import Path
from typing import Dict, Optional, Set

logger = logging.getLogger(__name__)

# ---- 系统级进程黑名单（不可修改） ----
SYSTEM_PROCESS_BLACKLIST = {
    'lockapp.exe', 'scrnsave.exe', 'screensaver.exe', 'ribbons.scr',
    'mystify.scr', 'bubbles.scr', 'aurora.scr',
    'logonui.exe', 'winlogon.exe', 'dwm.exe', 'explorer.exe',
    'shellexperiencehost.exe', 'startmenuexperiencehost.exe',
    'searchhost.exe', 'searchui.exe', 'cortana.exe',
    'textinputhost.exe', 'runtimebroker.exe',
    'idle', '',
}

# ---- 辅助进程黑名单（不可修改） ----
HELPER_EXE_BLACKLIST = {
    'unins000.exe', 'uninstall.exe', 'setup.exe', 'install.exe',
    'uninst.exe', 'uninstaller.exe',
    'vcredist_x64.exe', 'vcredist_x86.exe', 'vcredist.exe',
    'vc_redist.x64.exe', 'vc_redist.x86.exe', 'vc_redist.arm64.exe',
    'directx.exe', 'dxsetup.exe', 'dotnet.exe', 'dotnetfx.exe',
    'ndp472-kb4054530-x86-x64-allos-enu.exe',
    'ndp48-x86-x64-allos-enu.exe', 'ndp451-kb2859818-web.exe',
    'unitycrashhandler64.exe', 'unitycrashhandler32.exe',
    'crashpad_handler.exe', 'breakpad_server.exe', 'crash_handler.exe',
    'report.exe', 'bugreporter.exe', 'crash_report.exe',
    'ue4crashreporterclient.exe', 'ue4prereqsetup_x64.exe',
    'launcher.exe', 'redprelauncher.exe', 'steamwebhelper.exe',
    'modtools.exe', 'steamworkscommonredistributables.exe',
    'prereqsetup_x64.exe', 'prereqsetup_x86.exe',
    'easyanticheat.exe', 'easyanticheat_setup.exe',
    'battleye.exe', 'beclient.exe',
    'galaxyclient helper.exe', 'cefprocess.exe',
}

# ---- 已知游戏白名单（兜底） ----
KNOWN_GAMES = {
    'yuanshen.exe': '原神',
    'genshinimpact.exe': '原神',
    'starrail.exe': '崩坏：星穹铁道',
    'zenlesszonezeero.exe': '绝区零',
    'bh3.exe': '崩坏3',
    'cyberpunk2077.exe': '赛博朋克 2077',
    'witcher3.exe': '巫师3',
    'mhyx.exe': '明日方舟',
    # wegame.exe 已移至 GAME_LAUNCHERS，此处不重复
}

# ---- 游戏平台启动器（自身不算游戏，不可修改） ----
GAME_LAUNCHERS = {
    'steam.exe', 'epicgameslauncher.exe', 'battle.net.exe',
    'galaxyclient.exe', 'origin.exe', 'ea desktop.exe',
    'ubisoft connect.exe', 'xboxpcapp.exe', 'wegame.exe',
    'wallpaper64.exe', 'wallpaper32.exe',
}

# ---- 默认浏览器列表 ----
DEFAULT_BROWSERS = {
    'msedge.exe', 'chrome.exe', 'firefox.exe',
    'brave.exe', 'opera.exe', 'vivaldi.exe', 'arc.exe',
}


class AppClassifier:
    """应用分类器（配置驱动）"""

    def __init__(self, config_manager=None, cache_file: str | None = None):
        """
        Args:
            config_manager: ConfigManager 实例，用于读取浏览器/忽略名单/自定义分类
            cache_file: 游戏缓存文件路径
        """
        self._config = config_manager
        self.cache_file = cache_file or self._get_default_cache_path()
        self.steam_games: Dict[str, str] = {}  # exe -> 游戏名
        self.extra_games: Dict[str, str] = {}
        self._load_cached_games()
        if not self.steam_games and not self.extra_games:
            self.refresh_all_games()

    @staticmethod
    def detect_installed_browsers() -> Set[str]:
        """从注册表 App Paths 检测已安装的浏览器"""
        found: Set[str] = set()
        try:
            base = r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths'
            for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    with winreg.OpenKey(hive, base) as root:
                        i = 0
                        while True:
                            try:
                                key_name = winreg.EnumKey(root, i).lower()
                                i += 1
                                if key_name in DEFAULT_BROWSERS:
                                    found.add(key_name)
                            except OSError:
                                break
                except OSError:
                    pass
        except Exception:
            pass
        return found

    @property
    def browsers(self) -> Set[str]:
        """浏览器列表（配置合并默认）"""
        custom = set()
        if self._config:
            for b in self._config.browsers:
                custom.add(b.lower())
        return DEFAULT_BROWSERS | custom

    @property
    def installed_browsers(self) -> Set[str]:
        """实际检测到的浏览器（已安装 + 正在运行 + 自定义）"""
        installed = self.detect_installed_browsers()
        custom = set()
        if self._config:
            for b in self._config.browsers:
                custom.add(b.lower())
        return installed | custom

    def _get_default_cache_path(self) -> str:
        from .constants import STEAM_CACHE_PATH
        STEAM_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        return str(STEAM_CACHE_PATH)

    # ---- Steam 扫描 ----

    def _get_steam_install_path(self) -> Optional[str]:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r'Software\Valve\Steam') as key:
                steam_path, _ = winreg.QueryValueEx(key, 'SteamPath')
                return steam_path
        except (OSError, FileNotFoundError):
            pass
        for path in [r'C:\Program Files (x86)\Steam', r'C:\Program Files\Steam',
                     r'D:\Steam', r'D:\Games\Steam']:
            if os.path.exists(os.path.join(path, 'steam.exe')):
                return path
        return None

    def _get_steam_library_folders(self, steam_path: str) -> list[str]:
        folders = [steam_path]
        vdf_path = Path(steam_path) / 'steamapps' / 'libraryfolders.vdf'
        if vdf_path.exists():
            try:
                content = vdf_path.read_text(encoding='utf-8')
                for m in re.finditer(r'"path"\s*"([^"]+)"', content):
                    lib = m.group(1).replace('\\\\', '\\')
                    if lib not in folders:
                        folders.append(lib)
            except Exception:
                pass
        return folders

    def _parse_acf(self, acf_path: Path):
        try:
            content = acf_path.read_text(encoding='utf-8')
            name = re.search(r'"name"\s*"([^"]+)"', content)
            installdir = re.search(r'"installdir"\s*"([^"]+)"', content)
            if name and installdir:
                return name.group(1), installdir.group(1)
        except Exception:
            pass
        return None

    def _pick_main_exe(self, game_dir: Path) -> Optional[str]:
        def _best_exe(folder: Path) -> tuple[Optional[str], int]:
            exe_files = [f for f in folder.glob('*.exe')
                         if f.name.lower() not in HELPER_EXE_BLACKLIST]
            if not exe_files:
                return None, 0
            try:
                exe_files.sort(key=lambda f: f.stat().st_size, reverse=True)
                return exe_files[0].name.lower(), exe_files[0].stat().st_size
            except Exception:
                return exe_files[0].name.lower(), 0

        result, _ = _best_exe(game_dir)
        if result:
            return result

        best_size = 0
        best_name = None
        try:
            for sub in game_dir.rglob('*.exe'):
                try:
                    depth = len(sub.relative_to(game_dir).parts) - 1
                except ValueError:
                    continue
                if depth > 3:
                    continue
                if sub.name.lower() in HELPER_EXE_BLACKLIST:
                    continue
                try:
                    sz = sub.stat().st_size
                    if sz > best_size:
                        best_size = sz
                        best_name = sub.name.lower()
                except Exception:
                    pass
        except Exception:
            pass
        return best_name

    def _refresh_steam_games(self) -> int:
        steam_path = self._get_steam_install_path()
        if not steam_path:
            logger.info('未找到 Steam 安装路径')
            return 0
        new_games: Dict[str, str] = {}
        for lib_path in self._get_steam_library_folders(steam_path):
            steamapps = Path(lib_path) / 'steamapps'
            if not steamapps.exists():
                continue
            for acf_file in steamapps.glob('appmanifest_*.acf'):
                result = self._parse_acf(acf_file)
                if not result:
                    continue
                game_name, install_dir = result
                game_dir = steamapps / 'common' / install_dir
                if not game_dir.exists():
                    continue
                exe_name = self._pick_main_exe(game_dir)
                if exe_name:
                    if exe_name in HELPER_EXE_BLACKLIST:
                        continue
                    if exe_name in {x.lower() for x in GAME_LAUNCHERS}:
                        continue
                    new_games[exe_name] = game_name
                    logger.debug('Steam 游戏: %s -> %s', game_name, exe_name)
        self.steam_games = new_games
        logger.info('Steam 共识别 %d 个游戏主进程', len(new_games))
        return len(new_games)

    # ---- 米哈游 & 非 Steam ----

    def _refresh_mihoyo_games(self) -> int:
        found: Dict[str, str] = {}
        try:
            base = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base) as hive:
                i = 0
                while True:
                    try:
                        sub_name = winreg.EnumKey(hive, i)
                        i += 1
                        with winreg.OpenKey(hive, sub_name) as sub:
                            try:
                                disp, _ = winreg.QueryValueEx(sub, 'DisplayName')
                                loc, _ = winreg.QueryValueEx(sub, 'InstallLocation')
                                if any(x in disp for x in
                                       ['原神', 'Genshin', '星穹铁道', 'Star Rail',
                                        '绝区零', 'Zenless', '崩坏3']):
                                    self._probe_mihoyo_dir(loc, disp, found)
                            except (OSError, FileNotFoundError):
                                pass
                    except OSError:
                        break
        except Exception:
            pass

        search_roots = [d + '\\' for d in ['C:', 'D:', 'E:', 'F:'] if os.path.exists(d)]
        candidate_dirs = [
            'Genshin Impact', 'Genshin Impact bilibili',
            'Star Rail', 'StarRail',
            'ZenlessZoneZero', 'Zenless Zone Zero',
            'HoYoPlay', 'miHoYo',
        ]
        for root in search_roots:
            for d in candidate_dirs:
                path = os.path.join(root, d)
                if os.path.isdir(path):
                    self._probe_mihoyo_dir(path, d, found)
            for sub in ['app', 'Games', 'Game']:
                sub_root = os.path.join(root, sub)
                if os.path.isdir(sub_root):
                    try:
                        for d in os.listdir(sub_root):
                            if any(x in d for x in
                                   ['Genshin', 'Star Rail', 'StarRail',
                                    'Zenless', 'bilibili', 'miHoYo']):
                                self._probe_mihoyo_dir(os.path.join(sub_root, d), d, found)
                    except PermissionError:
                        pass

        import psutil
        for exe, name in KNOWN_GAMES.items():
            if exe not in found:
                try:
                    for p in psutil.process_iter(['name']):
                        if p.info['name'] and p.info['name'].lower() == exe:
                            found[exe] = name
                            break
                except Exception:
                    pass

        self.extra_games = found
        if found:
            logger.info('非 Steam 游戏: %s', list(found.items()))
        return len(found)

    def _probe_mihoyo_dir(self, base_dir: str, label: str, found: dict) -> None:
        target_exes = {
            'yuanshen.exe': '原神', 'genshinimpact.exe': '原神',
            'starrail.exe': '崩坏：星穹铁道', 'hkrpg.exe': '崩坏：星穹铁道',
            'zenlesszonezeero.exe': '绝区零', 'bh3.exe': '崩坏3',
        }
        try:
            for root, dirs, files in os.walk(base_dir):
                depth = root.replace(base_dir, '').count(os.sep)
                if depth > 4:
                    dirs.clear()
                    continue
                for f in files:
                    fl = f.lower()
                    if fl in target_exes:
                        found[fl] = target_exes[fl]
                        logger.debug('发现游戏: %s -> %s', target_exes[fl], f)
        except PermissionError:
            pass

    # ---- 公共方法 ----

    def refresh_all_games(self) -> None:
        self._refresh_steam_games()
        self._refresh_mihoyo_games()
        self._save_cached_games()

    def _load_cached_games(self) -> None:
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # 兼容旧格式（list）和新格式（dict）
                games = data.get('games', [])
                if isinstance(games, list):
                    self.steam_games = {e: e.replace('.exe', '') for e in games}
                else:
                    self.steam_games = games
                self.extra_games = data.get('extra_games', {})
                total = len(self.steam_games) + len(self.extra_games)
                logger.info('从缓存加载了 %d 个游戏', total)
        except Exception as e:
            logger.warning('加载缓存失败: %s', e)
            self.steam_games = {}
            self.extra_games = {}

    def _save_cached_games(self) -> None:
        try:
            from .constants import STEAM_CACHE_PATH
            STEAM_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'games': dict(self.steam_games),
                    'extra_games': self.extra_games,
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning('保存缓存失败: %s', e)

    def should_skip(self, process_name: str, exe_path: str = '') -> bool:
        """判断该进程是否应跳过（系统黑名单 + 忽略名单）"""
        if process_name.lower() in SYSTEM_PROCESS_BLACKLIST:
            return True
        if exe_path and self._config and self._config.is_ignored(exe_path):
            return True
        return False

    def classify(self, process_name: str, window_title: str = '',
                 exe_path: str = '') -> str:
        """分类进程（优先级：忽略 > 自定义分类 > 浏览器 > 启动器 > 游戏 > 兜底）"""
        proc_lower = process_name.lower()

        if proc_lower in SYSTEM_PROCESS_BLACKLIST:
            return 'skip'
        if exe_path and self._config and self._config.is_ignored(exe_path):
            return 'skip'

        # 用户自定义分类
        if exe_path and self._config:
            custom_cat = self._config.get_custom_category_for_exe(exe_path)
            if custom_cat:
                return custom_cat['name']

        if proc_lower in self.browsers:
            return 'browser'
        if proc_lower in GAME_LAUNCHERS:
            return 'other'
        # 动态扫描游戏库（Steam/米哈游）
        if proc_lower in self.steam_games or proc_lower in self.extra_games:
            return 'game'
        # 静态白名单兜底（KNOWN_GAMES）
        if proc_lower in KNOWN_GAMES:
            return 'game'
        return 'other'

    def get_game_name(self, process_name: str) -> str:
        proc_lower = process_name.lower()
        if proc_lower in self.steam_games:
            return self.steam_games[proc_lower]
        if proc_lower in self.extra_games:
            return self.extra_games[proc_lower]
        return process_name.replace('.exe', '')

    def get_category_display_name(self, category: str) -> str:
        from .constants import CATEGORY_NAMES
        if category == 'skip':
            return '跳过'
        return CATEGORY_NAMES.get(category, category)

    @property
    def all_game_exes(self) -> Set[str]:
        return self.steam_games | set(self.extra_games.keys())
