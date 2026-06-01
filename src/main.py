"""
UsageTracker 主入口
- 单实例检测
- 首次启动隐私声明
- 初始化所有模块
- 启动追踪 + 托盘
"""

import logging
import os
import sys
import threading
from datetime import datetime
from pathlib import Path

# 设置日志
LOG_FORMAT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
LOG_LEVEL = logging.INFO

# ---- 初始化日志 ----
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


def _create_icon():
    """创建托盘图标（优先 PNG，回退 ICO，最后程序化生成）"""
    if getattr(sys, 'frozen', False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent.parent
    from PIL import Image

    # 优先用 PNG（最可靠，无 ICO 解析问题）
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


def _get_exe_path():
    """获取可执行文件路径（用于启动管理）"""
    if getattr(sys, 'frozen', False):
        return sys.executable
    else:
        return str(Path(__file__).resolve().parent.parent / 'UsageTracker.exe')


def _run_app():
    """主应用逻辑"""
    _setup_logging()
    logger = logging.getLogger('main')
    logger.info('UsageTracker 启动中...')

    from src.constants import migrate_from_legacy
    migrate_from_legacy()

    # 单实例检测
    from src.singleton import SingleInstance
    instance = SingleInstance()
    if instance.already_running:
        logger.info('已有实例运行，退出')
        import ctypes
        from src.i18n import t
        ctypes.windll.user32.MessageBoxW(0, t('singleton.running'), t('dialog.hint'), 0x40)
        return 0

    # 加载配置
    from src.config_manager import ConfigManager
    from src.startup_manager import StartupManager
    from src.i18n import init as init_i18n
    config = ConfigManager()

    # 恢复日志等级（如果之前设置过）
    saved_level = config.get('log_level', 'INFO')
    if saved_level != 'INFO':
        _level_map = {'DEBUG': logging.DEBUG, 'WARNING': logging.WARNING, 'ERROR': logging.ERROR}
        if saved_level in _level_map:
            root = logging.getLogger()
            root.setLevel(_level_map[saved_level])
            for h in root.handlers:
                h.setLevel(_level_map[saved_level])

    # 首次运行处理
    # 用局部变量保存，供后续判断是否需要打开引导页
    _need_onboarding = bool(getattr(config, 'first_run', True) or not getattr(config, 'privacy_accepted', False))

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
    from src.crash_handler import CrashHandler

    data_store = DataStore()
    data_store.cleanup_expired_data(config.data_retention)

    classifier = AppClassifier(config_manager=config)
    reporter = HTMLReportGenerator()
    reporter.set_data_store(data_store)
    tracker = UsageTracker(check_interval=config.check_interval,
                            detection_mode='polling')
    notifier = UsageNotifier()
    crash_handler = CrashHandler()

    # 启动管理
    _exe_path = _get_exe_path()
    import sys as _sys
    if getattr(_sys, 'frozen', False):
        _install_dir = Path(_exe_path).parent
        _is_test_run = ('dist' in _install_dir.parts or
                        str(_install_dir).lower().startswith(
                            str(Path(__file__).resolve().parent.parent).lower()))
    else:
        _is_test_run = True
    startup = StartupManager(exe_path=_exe_path)
    if _is_test_run:
        logger.info('测试运行模式：跳过开机自启写入')
    elif config.auto_start and not startup.is_startup_enabled():
        startup.enable_startup()

    # Bridge 通信（HTTP + 文件轮询）
    bridge = BridgeHandler()
    bridge.start_http_server(config_manager=config, data_store=data_store, exe_path=_exe_path)
    bridge.start_polling(config_manager=config, data_store=data_store)

    # 首次运行：Bridge 启动后打开引导页
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

    # 创建托盘
    icon = _create_icon()
    tray_app = None
    _shutdown_event = threading.Event()

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
        if tray_app:
            tray_app.stop()

    # 尝试启动托盘（失败不致命，HTTP 服务继续运行）
    _tray_ok = False
    try:
        from src.tray_app import TrayApp
        tray_app_obj = TrayApp(
            icon_image=icon,
            data_store=data_store,
            config_manager=config,
            report_generator=reporter,
            on_settings=_open_settings,
            on_quit=_on_quit,
        )
        tray_app = tray_app_obj
        _tray_ok = True
        logger.info('托盘图标初始化成功')
    except Exception as e:
        logger.error('托盘初始化失败（HTTP 服务继续运行）: %s', e, exc_info=True)
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0,
            f'UsageTracker 托盘图标创建失败，程序将在后台运行。\n'
            f'如需退出，请使用任务管理器。\n\n错误: {e}',
            'UsageTracker - 警告',
            0x40,
        )

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
            # 关键：托盘运行在独立线程，崩溃不影响主进程和 HTTP
            import time as _time

            def _tray_loop():
                """托盘线程：pystray 崩溃时自动重启"""
                local_tray = tray_app_obj
                while not _shutdown_event.is_set():
                    try:
                        local_tray.run()
                        # 正常退出（用户点了退出）
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

        # 主线程：等待退出信号（保持进程存活）
        _shutdown_event.wait()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error('主循环异常: %s', e, exc_info=True)
        return 1

    logger.info('UsageTracker 已退出')
    return 0


def main():
    """入口函数（被 crash_handler 包装）"""
    return _run_app()


if __name__ == '__main__':
    from src.crash_handler import CrashHandler
    CrashHandler().wrap(main)
