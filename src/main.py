"""
UsageTracker 主入口 - Linux-first CLI
- 命令行参数解析: daemon / status / stop / web / today
- 单实例检测 | 首次启动隐私声明 | 初始化所有模块
- 启动追踪（headless 模式默认不初始化托盘）
- 保留 WebUI 设置界面 (http://127.0.0.1:19234)
"""

import argparse
import logging
import os
import signal
import sys
import threading
from datetime import datetime, date
from pathlib import Path

# 兼容直接运行 `python3 src/main.py` 与模块运行 `python3 -m src.main`。
# 直接运行时 sys.path 只包含 src/，需要把项目根目录加入后续 `from src...` 导入才可靠。
if __package__ in (None, ''):
    _PROJECT_ROOT = Path(__file__).resolve().parent.parent
    if str(_PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(_PROJECT_ROOT))

# 设置日志
LOG_FORMAT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
LOG_LEVEL = logging.INFO


# ── 锁 / PID 文件路径（与 FileLockSingleInstance 保持一致） ──────────

def _get_lock_path() -> Path:
    """返回单实例锁文件路径（与 singleton.py 中一致）。"""
    runtime = os.environ.get('XDG_RUNTIME_DIR')
    if runtime:
        lock_dir = Path(runtime)
    else:
        lock_dir = Path.home() / '.cache'
    return lock_dir / 'UsageTracker.lock'


def _read_pid_from_lock() -> int | None:
    """读取锁文件中的 PID，若文件不存在或格式错误返回 None。"""
    lock_path = _get_lock_path()
    if not lock_path.exists():
        return None
    try:
        pid_str = lock_path.read_text().strip()
        return int(pid_str) if pid_str else None
    except (ValueError, OSError):
        return None


def _get_lock_owner_pid() -> int | None:
    """Linux: 当锁文件 PID 丢失时，从 /proc/locks 反查持锁进程 PID。"""
    if os.name == 'nt':
        return None
    lock_path = _get_lock_path()
    try:
        st = lock_path.stat()
        target_inode = str(st.st_ino)
        target_dev_hex = f'{os.major(st.st_dev):02x}:{os.minor(st.st_dev):02x}'
        for line in Path('/proc/locks').read_text().splitlines():
            parts = line.split()
            # Example: 1: FLOCK ADVISORY WRITE 50500 00:33:176 0 EOF
            if len(parts) < 6:
                continue
            pid_text = parts[4]
            dev_inode = parts[5]
            fields = dev_inode.split(':')
            if len(fields) < 3:
                continue
            dev_hex = ':'.join(fields[:2]).lower()
            inode = fields[2]
            if inode == target_inode and dev_hex == target_dev_hex:
                pid = int(pid_text)
                return pid if _is_pid_alive(pid) else None
    except Exception:
        return None
    return None


def _cleanup_lock_file() -> None:
    """Best-effort 清理未被持有的旧锁文件。"""
    lock_path = _get_lock_path()
    try:
        lock_path.unlink(missing_ok=True)
    except OSError:
        # 状态命令不应因清理失败而阻断；下次 daemon 获取 fcntl 锁仍可覆盖。
        pass


def _is_pid_alive(pid: int | None) -> bool:
    """用 psutil 判活，避免 os.kill(pid, 0) 误判和规则禁用。"""
    if pid is None or pid <= 0:
        return False
    try:
        import psutil
        proc = psutil.Process(pid)
        return proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
    except Exception:
        return False


def _get_daemon_lock_status() -> tuple[bool, int | None]:
    """返回 (lock_held, pid)。

    FileLockSingleInstance 使用 fcntl 记录真实单实例状态，进程正常退出后
    可能留下包含旧 PID 的普通文件。因此 status/web 必须以 fcntl 锁是否仍被
    持有为准，而不是只看 PID 文本。
    """
    lock_path = _get_lock_path()
    if not lock_path.exists():
        return False, None
    pid = _read_pid_from_lock()
    if os.name == 'nt':
        return _is_pid_alive(pid), pid
    try:
        import fcntl
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with open(lock_path, 'a+') as fh:
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                if pid is None:
                    pid = _get_lock_owner_pid()
                return True, pid
            else:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
                _cleanup_lock_file()
                return False, pid
    except Exception:
        # fcntl 探测失败时降级到 psutil 判活；仍然不使用 os.kill(pid, 0)。
        alive = _is_pid_alive(pid)
        if not alive:
            _cleanup_lock_file()
        return alive, pid


# ── 日志 ──────────────────────────────────────────────────────────────

def _setup_logging():
    from src.constants import LOG_DIR
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f'usage_tracker_{datetime.now():%Y%m%d}.log'
    handlers = [logging.FileHandler(log_file, encoding='utf-8')]
    # 开发模式保留控制台输出，打包后静默
    if not getattr(sys, 'frozen', False):
        handlers.append(logging.StreamHandler())
    logging.basicConfig(
        level=LOG_LEVEL,
        format=LOG_FORMAT,
        handlers=handlers,
    )


# ── 图标（仅托盘使用，延迟导入 PIL） ──────────────────────────────

def _create_icon():
    """创建托盘图标（优先 PNG，回退 ICO，最后程序化生成）"""
    if getattr(sys, 'frozen', False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent.parent
    from PIL import Image  # 延迟导入

    # 优先用 PNG
    png_path = base / 'assets' / 'logo.png'
    if png_path.exists():
        try:
            img = Image.open(png_path).convert('RGBA')
            img = img.resize((64, 64), Image.LANCZOS)
            return img
        except Exception:
            pass

    # 回退 ICO
    ico_path = base / 'assets' / 'icon.ico'
    if ico_path.exists() and ico_path.stat().st_size > 500:
        try:
            img = Image.open(ico_path)
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            img = img.resize((64, 64), Image.LANCZOS)
            return img
        except Exception:
            pass

    # 最后手段：程序化生成
    from PIL import ImageDraw
    size = 32
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([2, 2, size - 3, size - 3], fill='#4361ee')
    draw.text((9, 7), 'U', fill='white')
    return img


# ── 可执行路径 ──────────────────────────────────────────────────────

def _get_exe_path():
    """获取可执行文件路径（用于启动管理）"""
    if getattr(sys, 'frozen', False):
        return sys.executable
    else:
        # Linux-first: 返回当前脚本路径
        return str(Path(__file__).resolve())


# ══════════════════════════════════════════════════════════════════════
#  命令实现
# ══════════════════════════════════════════════════════════════════════

def _run_daemon(headless: bool = True):
    """主应用逻辑：追踪器 + Bridge HTTP + WebUI（可选托盘）"""
    _setup_logging()
    logger = logging.getLogger('main')
    logger.info('UsageTracker 启动中... (headless=%s)', headless)

    from src.constants import migrate_from_legacy
    migrate_from_legacy()

    # 单实例检测
    from src.singleton import SingleInstance
    instance = SingleInstance()
    if instance.already_running:
        logger.info('已有实例运行，退出')
        print('UsageTracker: 已有实例运行中。使用 "python -m src.main status" 查看状态。')
        return 0

    # 加载配置
    from src.config_manager import ConfigManager
    from src.startup_manager import StartupManager
    from src.i18n import init as init_i18n
    config = ConfigManager()

    # 首次运行处理
    _need_onboarding = bool(
        getattr(config, 'first_run', True) or not getattr(config, 'privacy_accepted', False)
    )

    if config.first_run:
        logger.info('首次运行，清除首次运行标志')
        config.first_run = False
        config.save()

    init_i18n(config.language)

    # 初始化模块
    from src.data_store import DataStore
    from src.app_classifier import AppClassifier
    from src.reporter import HTMLReportGenerator
    from src.tracker import UsageTracker
    from src.notifier import UsageNotifier
    from src.bridge_handler import BridgeHandler

    data_store = DataStore()
    data_store.cleanup_expired_data(config.data_retention)

    classifier = AppClassifier(config_manager=config)
    reporter = HTMLReportGenerator()
    reporter.set_data_store(data_store)
    tracker = UsageTracker(check_interval=config.check_interval,
                            detection_mode='polling')
    notifier = UsageNotifier()

    # 启动管理
    _exe_path = _get_exe_path()
    import sys as _sys
    if getattr(_sys, 'frozen', False):
        _install_dir = Path(_exe_path).parent
        _is_test_run = (
            'dist' in _install_dir.parts
            or str(_install_dir).lower().startswith(
                str(Path(__file__).resolve().parent.parent).lower()
            )
        )
    else:
        _is_test_run = True
    startup = StartupManager(exe_path=_exe_path)
    if _is_test_run:
        logger.info('测试运行模式：跳过开机自启写入')
    elif config.auto_start and not startup.is_startup_enabled():
        startup.enable_startup()

    # Bridge HTTP + 轮询
    bridge = BridgeHandler()
    bridge.start_http_server(config_manager=config, data_store=data_store, exe_path=_exe_path)
    bridge.start_polling(config_manager=config, data_store=data_store)

    # 首次运行：打开引导页
    if _need_onboarding and not getattr(config, '_onboarding_shown', False):
        def _open_onboarding():
            import time
            time.sleep(2)
            import webbrowser
            try:
                webbrowser.open('http://127.0.0.1:19234/onboarding')
                logger.info('已打开首次运行引导页')
                config._onboarding_shown = True
            except Exception as e:
                logger.error('打开引导页失败: %s', e)
        threading.Thread(target=_open_onboarding, daemon=True).start()

    # 自动保存定时器
    from src.constants import AUTO_SAVE_INTERVAL, MIN_AUTO_SAVE_DURATION

    _last_saved_dur: dict[int, float] = {}

    def _save_session_data(session):
        try:
            cat = classifier.classify(
                session.name, session.window_title, session.exe_path)
            if cat == 'skip':
                return
            sid = id(session)
            prev = _last_saved_dur.get(sid, 0.0)
            delta = session.duration_seconds - prev
            if delta < 1:
                return
            data_store.save_session(
                session.name, cat, delta,
                session.start_time.date().isoformat(),
                session.exe_path)
            _last_saved_dur[sid] = session.duration_seconds
        except Exception as e:
            logger.error('保存 session 数据失败: %s', e)

    def _auto_save():
        while not tracker._stop_event.is_set():
            tracker._stop_event.wait(AUTO_SAVE_INTERVAL)
            if tracker._stop_event.is_set():
                break
            for session in tracker.sessions:
                if session.duration_seconds < MIN_AUTO_SAVE_DURATION:
                    continue
                _save_session_data(session)
            if tracker.current_session:
                tracker._update_current_duration()
                _save_session_data(tracker.current_session)

    save_thread = threading.Thread(target=_auto_save, daemon=True, name='auto-save')
    save_thread.start()

    # 通知回调
    def _on_session_end(old_session, new_session):
        try:
            if not old_session:
                return
            cat = classifier.classify(
                old_session.name, old_session.window_title, old_session.exe_path)
            if cat != 'skip' and old_session.duration_seconds >= MIN_AUTO_SAVE_DURATION:
                _save_session_data(old_session)
            if cat in ('skip', 'other'):
                return
            from datetime import date as _date
            today = _date.today().isoformat()
            records = data_store.get_daily_usage(today)
            total = sum(r.duration_seconds for r in records if r.category == cat)
            alerts = notifier.update_usage(cat, total)
            for alert in alerts:
                data_store.save_alert(cat, alert)
        except Exception as e:
            logger.error('_on_session_end 异常: %s', e, exc_info=True)

    tracker.on_app_switch = _on_session_end

    # 设置窗口回调
    def _open_settings():
        logger.info('打开网页端设置')
        import webbrowser
        try:
            webbrowser.open('http://127.0.0.1:19234/settings')
        except Exception as e:
            logger.error('打开浏览器失败: %s', e)

    # ── 退出事件 ───────────────────────────────────────────────────
    _shutdown_event = threading.Event()
    _tray_app_ref = None

    def _on_quit():
        _shutdown_event.set()
        logger.info('正在退出...')
        tracker._update_current_duration()
        if tracker.current_session:
            _save_session_data(tracker.current_session)
        for session in tracker.sessions:
            _save_session_data(session)
        tracker.stop()
        bridge.stop_polling()
        if _tray_app_ref:
            _tray_app_ref.stop()

    # ── 可选托盘 ───────────────────────────────────────────────────
    if not headless:
        try:
            icon = _create_icon()
            from src.tray_app import TrayApp
            tray_app_obj = TrayApp(
                icon_image=icon,
                data_store=data_store,
                config_manager=config,
                report_generator=reporter,
                on_settings=_open_settings,
                on_quit=_on_quit,
            )
            _tray_app_ref = tray_app_obj
            _tray_ok = True
            logger.info('托盘图标初始化成功')
        except Exception as e:
            logger.error('托盘初始化失败（headless 模式继续运行）: %s', e, exc_info=True)
            _tray_ok = False
            print(f'UsageTracker: 托盘初始化失败（{e}），继续 headless 运行。')
    else:
        _tray_ok = False

    # ── 启动追踪 ───────────────────────────────────────────────────
    print(f'UsageTracker v{__import__("src.version", fromlist=["VERSION"]).VERSION} 已启动'
          f' ({"headless" if headless else "with tray"})')
    print(f'WebUI: http://127.0.0.1:19234')
    print(f'停止: Ctrl+C 或运行 "python -m src.main stop"')

    try:
        tracker.start()
        logger.info('UsageTracker 已启动')

        # 启动时检查更新
        if config.check_update:
            logger.info('启动更新检查...')
            from src.updater import check_update_async
            from src.version import VERSION
            def _on_update_result(update_info):
                if update_info:
                    import webbrowser
                    logger.info('发现新版本: %s', update_info.get('version'))
                    webbrowser.open(update_info.get('url', ''))
                else:
                    logger.debug('更新检查完成：已是最新版')
            check_update_async(VERSION, callback=_on_update_result)

        # 开机自动弹出昨日报告
        if config.auto_show_daily_report and _tray_ok:
            today_str = datetime.now().date().isoformat()
            if config.last_report_shown_date != today_str:
                tray_app_obj._auto_open_daily = True
                config.last_report_shown_date = today_str
                config.save()

        if _tray_ok:
            import time as _time

            def _tray_loop():
                local_tray = tray_app_obj
                while not _shutdown_event.is_set():
                    try:
                        local_tray.run()
                        logger.info('托盘正常退出')
                        _shutdown_event.set()
                        break
                    except Exception as e:
                        logger.error('托盘崩溃，尝试重启: %s', e, exc_info=True)
                        if _shutdown_event.is_set():
                            break
                        _time.sleep(3)
                        try:
                            new_icon = _create_icon()
                            local_tray = TrayApp(
                                icon_image=new_icon,
                                data_store=data_store,
                                config_manager=config,
                                report_generator=reporter,
                                on_settings=_open_settings,
                                on_quit=_on_quit,
                            )
                            logger.info('托盘已重启')
                        except Exception as e2:
                            logger.error('托盘重启失败，放弃: %s', e2)
                            break

            _tray_thr = threading.Thread(
                target=_tray_loop, daemon=False, name='tray-icon')
            _tray_thr.start()

        # 主线程：等待退出信号
        _shutdown_event.wait()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error('主循环异常: %s', e, exc_info=True)
        return 1

    logger.info('UsageTracker 已退出')
    print('UsageTracker: 已停止')
    return 0


def _run_status():
    """检查运行状态并打印。"""
    lock_held, pid = _get_daemon_lock_status()
    if not lock_held:
        if pid is None:
            print('UsageTracker: 未运行')
        else:
            print(f'UsageTracker: 未运行（已清理旧锁 PID: {pid}）')
        return 0
    if pid is None:
        print('UsageTracker: 运行中 (PID: unknown)')
    else:
        print(f'UsageTracker: 运行中 (PID: {pid})')
    print(f'WebUI: http://127.0.0.1:19234')
    return 0


def _run_stop():
    """停止运行中的 daemon。"""
    lock_held, pid = _get_daemon_lock_status()
    if not lock_held or pid is None:
        print('UsageTracker: 未运行，无需停止')
        return 0
    try:
        import psutil
        proc = psutil.Process(pid)
        proc.terminate()
        print(f'UsageTracker: 已发送停止信号 (PID: {pid})')
        return 0
    except psutil.NoSuchProcess:
        print(f'UsageTracker: 进程 {pid} 已不存在，清除锁文件...')
        _cleanup_lock_file()
        return 0
    except psutil.AccessDenied:
        print(f'UsageTracker: 无权限停止进程 {pid}，请手动执行: kill {pid}')
        return 1
    except Exception as exc:
        print(f'UsageTracker: 停止进程 {pid} 失败: {exc}')
        return 1


def _run_web():
    """打开 WebUI 设置页面。"""
    import webbrowser
    url = 'http://127.0.0.1:19234/settings'
    lock_held, pid = _get_daemon_lock_status()
    if not lock_held:
        if pid is None:
            print(f'UsageTracker: 未运行，WebUI 不可用')
        else:
            print(f'UsageTracker: 旧锁 PID {pid} 已清理，WebUI 不可用')
        print(f'请先启动: python -m src.main daemon')
        return 1
    print(f'UsageTracker: 在浏览器中打开 {url}')
    webbrowser.open(url)
    return 0


def _run_today():
    """从数据库查询并打印今日使用统计。"""
    # 仅在 daemon 模式下才初始化日志和模块；today 是独立查询
    from src.data_store import DataStore
    from src.config_manager import ConfigManager

    try:
        config = ConfigManager()
        from src.i18n import init as init_i18n
        init_i18n(config.language)
        store = DataStore()
        today_iso = date.today().isoformat()
        records = store.get_daily_usage(today_iso)
        if not records:
            print(f'UsageTracker: {today_iso} 暂无使用记录')
            return 0
        total = sum(r.duration_seconds for r in records)
        from src.data_store import DataStore as DS
        print(f'📊 UsageTracker — {today_iso}')
        print(f'{"─" * 40}')
        print(f'总使用时长: {DS.format_duration(total)}')
        by_cat: dict[str, float] = {}
        for r in records:
            by_cat[r.category] = by_cat.get(r.category, 0) + r.duration_seconds
        for cat, secs in sorted(by_cat.items(), key=lambda x: -x[1]):
            print(f'  {cat}: {DS.format_duration(secs)}')
        print()
        # Top 5 应用
        from collections import Counter
        app_counter = Counter()
        for r in records:
            app_counter[r.app_name] += r.duration_seconds
        print('Top 应用:')
        for app, secs in app_counter.most_common(5):
            print(f'  {app}: {DS.format_duration(secs)}')
        return 0
    except Exception as e:
        print(f'UsageTracker: 查询失败 — {e}')
        return 1


# ══════════════════════════════════════════════════════════════════════
#  CLI 入口
# ══════════════════════════════════════════════════════════════════════

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='python -m src.main',
        description='UsageTracker — Linux-first 使用时长追踪工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
命令示例:
  python -m src.main               启动 daemon（前台，headless 无托盘）
  python -m src.main daemon        同上
  python -m src.main daemon --tray 启动 daemon（带托盘，需 pystray+Pillow）
  python -m src.main status        查看运行状态
  python -m src.main stop          停止 daemon
  python -m src.main web           打开 WebUI 设置页
  python -m src.main today         查看今日使用统计
        """,
    )
    parser.add_argument(
        'command', nargs='?', default='daemon',
        choices=['daemon', 'status', 'stop', 'web', 'today'],
        help='操作命令（默认: daemon）',
    )
    parser.add_argument(
        '--tray', action='store_true',
        help='启用系统托盘（需 pystray + Pillow）',
    )
    return parser


def main():
    """CLI 入口函数。"""
    parser = _build_parser()
    # 支持 -h / --help
    if len(sys.argv) >= 2 and sys.argv[1] in ('-h', '--help'):
        parser.print_help()
        return 0

    args = parser.parse_args()

    if args.command == 'daemon':
        return _run_daemon(headless=not args.tray)
    elif args.command == 'status':
        return _run_status()
    elif args.command == 'stop':
        return _run_stop()
    elif args.command == 'web':
        return _run_web()
    elif args.command == 'today':
        return _run_today()
    return 0


def _should_crash_wrap(argv: list[str] | None = None) -> bool:
    """Only daemon runs should use crash-restart wrapping.

    Short-lived CLI commands such as ``status`` and ``web`` may intentionally
    return non-zero codes (for example when the daemon is not running).  Treating
    those as crashes causes duplicate command output and spurious crash logs.
    """
    if argv is None:
        argv = sys.argv[1:]
    commands = {'daemon', 'status', 'stop', 'web', 'today'}
    explicit_commands = [arg for arg in argv if arg in commands]
    if not explicit_commands:
        return True
    return explicit_commands[0] == 'daemon'


if __name__ == '__main__':
    if _should_crash_wrap():
        from src.crash_handler import CrashHandler
        CrashHandler().wrap(main)
    else:
        sys.exit(main())
