"""
应用分类器（配置驱动）
- Linux-first 应用场景分类
- 识别浏览器、开发、终端、通讯、文档、办公、设计、系统等应用
- 支持自定义分类和忽略名单
"""

import logging
import sqlite3
import subprocess
from pathlib import Path

try:
    import winreg
except ImportError:  # non-Windows
    winreg = None
from typing import Set

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

# ---- 默认浏览器列表（跨平台） ----
DEFAULT_BROWSERS = {
    # Windows
    'msedge.exe', 'chrome.exe', 'firefox.exe',
    'brave.exe', 'opera.exe', 'vivaldi.exe', 'arc.exe',
    # Linux
    'firefox', 'firefox-esr', 'firefox-developer', 'icecat', 'librewolf',
    'chromium', 'chromium-browser', 'chrome', 'google-chrome', 'google-chrome-stable',
    'brave', 'brave-browser', 'brave-browser-stable',
    'opera', 'opera-browser', 'vivaldi', 'vivaldi-bin',
    'microsoft-edge', 'microsoft-edge-dev', 'microsoft-edge-stable', 'msedge',
    'epiphany', 'epiphany-browser', 'gnome-web', 'org.gnome.epiphany',
    'midori', 'falkon', 'konqueror', 'qutebrowser', 'nyxt', 'luakit',
    'floorp', 'zen', 'thorium-browser', 'ungoogled-chromium',
}

# ---- Linux 开发工具进程名（不含 .exe） ----
DEVELOPMENT_PROCESSES = {
    'code', 'code-oss', 'code-insiders',                       # VSCode
    'idea', 'idea-ultimate', 'idea-ce',                        # IntelliJ
    'pycharm', 'pycharm-professional', 'pycharm-community',    # PyCharm
    'webstorm', 'goland', 'datagrip', 'rider', 'phpstorm', 'clion',
    'android-studio', 'studio',                                # Android Studio
    'eclipse', 'netbeans', 'sublime_text', 'atom', 'brackets',
    'geany', 'kate', 'kdevelop', 'anjuta',
    'neovim', 'nvim', 'vim', 'gvim', 'emacs',
    'gitkraken', 'gitg', 'lazygit',
    'dbeaver', 'mysql-workbench', 'postgresql', 'pgadmin4',
    'jupyter', 'jupyter-lab', 'jupyter-notebook',
}

# ---- Linux 终端模拟器 ----
TERMINAL_PROCESSES = {
    'gnome-terminal', 'konsole', 'alacritty', 'kitty', 'terminator',
    'xterm', 'urxvt', 'rxvt', 'st',
    'tilix', 'termite', 'lxterminal', 'xfce4-terminal',
    'guake', 'yakuake', 'tilda',
    'wezterm', 'foot', 'footclient', 'hyper',
}

# ---- Linux 通讯工具 ----
COMMUNICATION_PROCESSES = {
    'discord', 'slack', 'element', 'telegram-desktop', 'telegram',
    'signal-desktop', 'whatsapp-nativefier', 'franz', 'rambox',
    'thunderbird', 'geary', 'evolution',
    'teams', 'teams-for-linux', 'zoom', 'skypeforlinux',
    'mattermost-desktop',
    'wechat', 'qq', 'dingtalk', 'feishu', 'lark',
}

# ---- Linux 文档/笔记工具 ----
DOCUMENTATION_PROCESSES = {
    'obsidian', 'logseq', 'notable', 'notion', 'notion-app', 'notion-enhanced',
    'zettlr', 'typora', 'marktext', 'ghostwriter',
    'xournal', 'xournalpp', 'okular', 'zathura', 'evince', 'atril',
    'calibre', 'calibre-gui',
}

# ---- Linux 办公套件 ----
OFFICE_PROCESSES = {
    'libreoffice', 'libreoffice-writer', 'libreoffice-calc', 'libreoffice-impress',
    'onlyoffice', 'onlyoffice-desktopeditors',
    'wps', 'wps-office',
    'abiword', 'gnumeric', 'calligrawords', 'calligrasheets',
}

# ---- Linux 影音媒体 ----
MEDIA_PROCESSES = {
    'vlc', 'mpv', 'totem', 'celluloid',
    'gnome-music', 'rhythmbox', 'spotify', 'clementine',
    'audacious', 'strawberry', 'deadbeef', 'cmus',
    'gimp', 'inkscape', 'krita', 'blender', 'darktable', 'rawtherapee',
    'shotwell', 'gthumb', 'eog', 'nomacs',
    'kdenlive', 'openshot', 'shotcut', 'obs', 'obs-studio',
    'simplescreenrecorder', 'peek', 'flameshot', 'shutter',
    'handbrake', 'pavucontrol',
}

# ---- Linux 系统工具 ----
SYSTEM_PROCESSES = {
    'gnome-system-monitor', 'ksysguard', 'htop',
    'gnome-control-center', 'gnome-settings', 'systemsettings',
    'gnome-disks', 'gparted', 'baobab',
    'gnome-calculator', 'gnome-calendar', 'gnome-clocks',
    'nautilus', 'nemo', 'thunar', 'pcmanfm', 'dolphin', 'caja',
    'gnome-characters', 'gnome-logs',
    'timeshift', 'deja-dup',
    'gufw', 'system-config-printer',
}

# ---- Linux AI/LLM 工具 ----
AI_PROCESSES = {
    'ollama', 'llama-server', 'llama-cli',
    'lm-studio', 'jan', 'jan-electron',
    'text-generation-webui', 'invoke-ai',
}

# ---- Linux 设计/3D ----
DESIGN_PROCESSES = {
    'gimp', 'inkscape', 'krita',
    'blender', 'freecad', 'openscad',
    'darktable', 'rawtherapee',
    'figma-linux',
    'scribus', 'pencil',
}

# ---- Linux 虚拟化 ----
VIRTUALIZATION_PROCESSES = {
    'virtualbox', 'virtualboxvm',
    'qemu', 'qemu-system-x86_64', 'qemu-system-aarch64',
    'virt-manager', 'gnome-boxes',
    'vmware', 'vmware-vmx',
    'docker', 'docker-compose', 'docker-desktop', 'podman',
    'kubectl', 'minikube', 'kind', 'k3d', 'containerd',
    'wine', 'wineserver', 'wine64', 'proton', 'lutris',
}


class AppClassifier:
    """应用分类器（配置驱动）"""

    def __init__(self, config_manager=None, cache_file: str | None = None):
        """
        Args:
            config_manager: ConfigManager 实例，用于读取浏览器/忽略名单/自定义分类
            cache_file: 分类器缓存文件路径
        """
        self._config = config_manager
        self.cache_file = cache_file or self._get_default_cache_path()
        self._load_cached_rules()

    @staticmethod
    def detect_installed_browsers() -> Set[str]:
        """检测已安装的浏览器。Windows 走注册表，Linux 走 xdg-mime + desktop/可执行文件扫描。"""
        browsers: Set[str] = set()
        if winreg is None:
            desktop_dirs = [
                Path('/usr/share/applications'),
                Path('/usr/local/share/applications'),
                Path.home() / '.local/share/applications',
                Path('/var/lib/flatpak/exports/share/applications'),
                Path.home() / '.local/share/flatpak/exports/share/applications',
            ]
            needles = {
                'firefox': 'firefox',
                'librewolf': 'librewolf',
                'icecat': 'icecat',
                'floorp': 'floorp',
                'zen': 'zen',
                'chromium': 'chromium',
                'chrome': 'google-chrome',
                'google-chrome': 'google-chrome',
                'brave': 'brave-browser',
                'opera': 'opera',
                'vivaldi': 'vivaldi',
                'edge': 'microsoft-edge',
                'microsoft-edge': 'microsoft-edge',
                'epiphany': 'epiphany',
                'gnome-web': 'gnome-web',
                'falkon': 'falkon',
                'qutebrowser': 'qutebrowser',
                'midori': 'midori',
            }

            def _add_desktop_name(name: str) -> None:
                stem = Path(name.strip()).name.replace('.desktop', '').lower()
                if not stem:
                    return
                for needle, canonical in needles.items():
                    if needle in stem:
                        browsers.add(canonical)
                        browsers.add(stem)

            # xdg-mime only reads desktop defaults; no system mutation.
            for scheme in ('x-scheme-handler/https', 'x-scheme-handler/http', 'text/html'):
                try:
                    result = subprocess.run(
                        ['xdg-mime', 'query', 'default', scheme],
                        capture_output=True, text=True, timeout=3
                    )
                    if result.returncode == 0:
                        _add_desktop_name(result.stdout)
                except Exception:
                    continue

            for directory in desktop_dirs:
                try:
                    for desktop in directory.glob('*.desktop'):
                        low = desktop.name.lower()
                        for needle, canonical in needles.items():
                            if needle in low:
                                browsers.add(canonical)
                                browsers.add(desktop.stem.lower())
                                break
                except Exception:
                    continue

            # which lookup catches AppImage/portable names on PATH.
            for candidate in DEFAULT_BROWSERS:
                try:
                    result = subprocess.run(
                        ['which', candidate], capture_output=True, text=True, timeout=1
                    )
                    if result.returncode == 0:
                        browsers.add(candidate)
                except Exception:
                    continue
            return browsers

        browser_names = {
            'chrome': 'chrome.exe', 'firefox': 'firefox.exe', 'edge': 'msedge.exe',
            'brave': 'brave.exe', 'opera': 'opera.exe', 'vivaldi': 'vivaldi.exe',
        }
        try:
            for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                try:
                    with winreg.OpenKey(root, r'SOFTWARE\Clients\StartMenuInternet') as key:
                        for i in range(winreg.QueryInfoKey(key)[0]):
                            sub = winreg.EnumKey(key, i).lower()
                            for needle, exe in browser_names.items():
                                if needle in sub:
                                    browsers.add(exe)
                except FileNotFoundError:
                    continue
        except Exception:
            pass
        return browsers

    def _configured_browser_names(self) -> Set[str]:
        """Return browser names from config, accepting both old list[str] and API list[dict]."""
        custom: Set[str] = set()
        if not self._config:
            return custom
        for item in getattr(self._config, 'browsers', []) or []:
            values = []
            if isinstance(item, str):
                values.append(item)
            elif isinstance(item, dict):
                values.extend([
                    item.get('name', ''),
                    item.get('exe_path', ''),
                    item.get('executable', ''),
                ])
            for value in values:
                name = Path(str(value).strip()).name.lower()
                if not name:
                    continue
                custom.add(name)
                if name.endswith('.desktop'):
                    custom.add(name[:-8])
                if name.endswith('.exe'):
                    custom.add(name[:-4])
        return custom

    @property
    def browsers(self) -> Set[str]:
        """浏览器列表（配置合并默认）"""
        return DEFAULT_BROWSERS | self._configured_browser_names()

    @property
    def installed_browsers(self) -> Set[str]:
        """实际检测到的浏览器（已安装 + 正在运行 + 自定义）"""
        installed = self.detect_installed_browsers()
        return installed | self._configured_browser_names()

    def _get_default_cache_path(self) -> str:
        from .constants import CLASSIFIER_CACHE_PATH
        CLASSIFIER_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        return str(CLASSIFIER_CACHE_PATH)

    # ---- 公共方法 ----

    def refresh_all_rules(self) -> None:
        """刷新分类规则。

        Linux-first 版本不再主动扫描平台专用目录；分类规则主要来自
        内置 Linux 应用场景表和用户在 WebUI 中维护的自定义分类。
        保留该方法是为了兼容旧调用方。
        """
        self._save_cached_rules()

    def _load_cached_rules(self) -> None:
        """加载分类器缓存。

        旧版本曾缓存平台扫描结果；Linux-first 版本不再使用这类
        缓存，因此这里只验证文件存在性，不恢复任何旧扫描状态。
        """
        return None

    def _save_cached_rules(self) -> None:
        """保存分类器缓存。当前无动态扫描规则，方法保留为 no-op。"""
        return None

    def should_skip(self, process_name: str, exe_path: str = '') -> bool:
        """判断该进程是否应跳过（系统黑名单 + 忽略名单）"""
        if process_name.lower() in SYSTEM_PROCESS_BLACKLIST:
            return True
        if exe_path and self._config and self._config.is_ignored(exe_path):
            return True
        return False

    def classify(self, process_name: str, window_title: str = '',
                 exe_path: str = '') -> str:
        """分类进程（优先级：忽略 > 自定义分类 > 浏览器 > Linux 场景分类 > 兜底）"""
        proc_lower = process_name.lower()

        if proc_lower in SYSTEM_PROCESS_BLACKLIST:
            return 'skip'
        if exe_path and self._config and self._config.is_ignored(exe_path):
            return 'skip'

        # 用户自定义分类（最高优先级）
        if exe_path and self._config:
            custom_cat = self._config.get_custom_category_for_exe(exe_path)
            if custom_cat:
                return custom_cat['name']

        # 浏览器（跨平台）
        if proc_lower in self.browsers:
            return 'browser'

        # ---- Linux-first 分类（按使用场景优先级） ----
        if proc_lower in DEVELOPMENT_PROCESSES:
            return 'development'
        if proc_lower in TERMINAL_PROCESSES:
            return 'terminal'
        if proc_lower in COMMUNICATION_PROCESSES:
            return 'communication'
        if proc_lower in DOCUMENTATION_PROCESSES:
            return 'document'
        if proc_lower in OFFICE_PROCESSES:
            return 'document'
        if proc_lower in DESIGN_PROCESSES:
            return 'development'
        if proc_lower in MEDIA_PROCESSES:
            return 'document'
        if proc_lower in SYSTEM_PROCESSES:
            return 'system'
        if proc_lower in AI_PROCESSES:
            return 'development'
        if proc_lower in VIRTUALIZATION_PROCESSES:
            return 'development'

        return 'other'

    def get_category_display_name(self, category: str) -> str:
        from .constants import CATEGORY_NAMES
        if category == 'skip':
            return '跳过'
        return CATEGORY_NAMES.get(category, category)

    def get_suggestions(self, min_seconds: float = 600,
                        top_n: int = 10) -> list[dict]:
        """分析“其他”分类中的应用，返回可直接展示的分类建议列表。"""
        suggestions: list[dict] = []
        if not self._config:
            return suggestions
        db_path = getattr(self._config, 'db_path', None) or getattr(self._config, 'data_path', None)
        if not db_path:
            try:
                from .constants import DB_PATH
                db_path = DB_PATH
            except Exception:
                db_path = None
        if not db_path:
            return suggestions
        try:
            db_path = Path(db_path).expanduser()
            if not db_path.exists():
                return suggestions
            sql = """
                SELECT app_name, COALESCE(category, '') AS category,
                       SUM(duration_seconds) AS total_seconds, COALESCE(exe_path, '') AS exe_path
                FROM usage_records
                GROUP BY app_name, category, exe_path
                HAVING total_seconds >= ?
                ORDER BY total_seconds DESC
                LIMIT ?
            """
            with sqlite3.connect(str(db_path)) as conn:
                rows = conn.execute(sql, (min_seconds, top_n * 4)).fetchall()
            seen: set[tuple[str, str]] = set()
            for app_name, current_category, secs, exe_path in rows:
                if not app_name:
                    continue
                guessed = self.classify(app_name, app_name, exe_path or '')
                # Only suggest actionable items: blank/other rows that can move to a concrete category,
                # or rows where the classifier changed its mind.
                if guessed in {'skip', 'other'}:
                    continue
                if current_category and current_category != 'other' and guessed == current_category:
                    continue
                key = (app_name.lower(), (exe_path or '').lower())
                if key in seen:
                    continue
                seen.add(key)
                suggestions.append({
                    'app_name': app_name,
                    'exe_path': exe_path or '',
                    'duration_seconds': float(secs or 0),
                    'category': current_category or 'other',
                    'suggested_category': guessed,
                    'suggested_category_name': self.get_category_display_name(guessed),
                })
                if len(suggestions) >= top_n:
                    break
        except Exception as e:
            logger.warning('获取分类建议失败: %s', e)
        return suggestions
