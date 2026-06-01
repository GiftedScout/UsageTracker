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
    """创建托盘图标（优先加载 assets/icon.ico，否则程序化生成）"""
    # 在 PyInstaller 打包后，assets 在 sys._MEIPASS 下
    if getattr(sys, 'frozen', False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent.parent
    icon_path = base / 'assets' / 'icon.ico'
    if icon_path.exists():
        try:
            from PIL import Image
            return Image.open(icon_path)
        except Exception:
            pass
    # 程序化生成 32x32 蓝色圆形图标（兜底）
    from PIL import Image, ImageDraw
    size = 32
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([2, 2, size - 3, size - 3], fill='#4361ee')
    draw.text((9, 7), 'U', fill='white')
    return img


def _show_privacy_dialog():
    """首次启动时显示隐私声明对话框"""
    import tkinter as tk
    from tkinter import ttk
    from src.config_manager import ConfigManager
    from src.i18n import init as init_i18n, t

    config = ConfigManager()
    # 隐私对话框在 i18n 初始化之前，先根据 config.language 加载
    init_i18n(config.language)
    if config.privacy_accepted:
        return config

    result = {'accepted': False}

    root = tk.Tk()
    root.title(t('privacy.title'))
    root.geometry('420x280')
    root.resizable(False, False)

    # 居中
    root.withdraw()
    root.update_idletasks()
    x = (root.winfo_screenwidth() - 420) // 2
    y = (root.winfo_screenheight() - 280) // 2
    root.geometry(f'+{x}+{y}')
    root.deiconify()

    ttk.Label(root, text=t('privacy.title'), font=('', 14, 'bold')).pack(pady=(20, 10))
    ttk.Label(root, text=t('privacy.content'),
              wraplength=380, justify='center').pack(pady=10)

    def on_accept():
        config.privacy_accepted = True
        config.save()
        result['accepted'] = True
        root.destroy()

    def on_decline():
        root.destroy()

    btn_frame = ttk.Frame(root)
    btn_frame.pack(pady=20)
    ttk.Button(btn_frame, text=t('privacy.accept'), command=on_accept).pack(side='left', padx=8)
    ttk.Button(btn_frame, text=t('privacy.decline'), command=on_decline).pack(side='left', padx=8)

    root.mainloop()
    return config if result['accepted'] else None


def _get_exe_path():
    """获取可执行文件路径（用于启动管理）"""
    import sys as _sys
    if getattr(_sys, 'frozen', False):
        # PyInstaller 打包后：_MEIPASS 上层就是 exe
        return _sys.executable
    else:
        # 开发模式：指向 src/main.py 的上层目录中的启动脚本（仅用于测试）
        return str(Path(__file__).resolve().parent.parent / 'UsageTracker.exe')


def _run_app():
    """主应用逻辑"""
    _setup_logging()
    logger = logging.getLogger('main')
    logger.info('UsageTracker 启动中...')

    # 从旧版路径迁移数据
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

    # 检查是否为首次运行（安装后）
    from src.config_manager import ConfigManager
    from src.startup_manager import StartupManager
    from src.i18n import init as init_i18n
    config = ConfigManager()
    
    # ── 创建持久化的隐藏 tk 根窗口（避免多次 Tk() 崩溃） ──
    import tkinter as _tk
    _tk_root = _tk.Tk()
    _tk_root.withdraw()
    
    if config.first_run:
        # 初始化国际化（onboarding 需要翻译）
        init_i18n(config.language)
        # 首次运行，显示引导界面
        logger.info('首次运行，显示引导界面')
        from ui.onboarding import OnboardingWindow
        onboarding_window = OnboardingWindow(_tk_root, config, StartupManager(exe_path=_get_exe_path()))
        onboarding_window.wait()  # 阻塞直到引导完成
        
        # 重新加载配置（因为可能在引导中被修改）
        config = ConfigManager()
        
        # 首次运行后仍需检查隐私声明
        if not config.privacy_accepted:
            init_i18n(config.language)
            if not _show_privacy_dialog():
                _tk_root.destroy()
                logger.info('用户未接受隐私声明，退出')
                return 0
    else:
        # 非首次运行，直接检查隐私声明
        init_i18n(config.language)
        if not config.privacy_accepted:
            if not _show_privacy_dialog():
                _tk_root.destroy()
                logger.info('用户未接受隐私声明，退出')
                return 0

    # 初始化国际化
    from src.i18n import init as init_i18n
    init_i18n(config.language)

    # 初始化模块（复用已接受隐私声明的 config，不再重新实例化）
    from src.data_store import DataStore
    from src.app_classifier import AppClassifier
    from src.reporter import HTMLReportGenerator
    from src.tracker import UsageTracker
    from src.notifier import UsageNotifier
    from src.bridge_handler import BridgeHandler
    from src.crash_handler import CrashHandler

    # config 已由 _show_privacy_dialog() 返回，此处不重新实例化
    data_store = DataStore()
    data_store.cleanup_expired_data(config.data_retention)

    classifier = AppClassifier(config_manager=config)
    reporter = HTMLReportGenerator()
    reporter.set_data_store(data_store)
    tracker = UsageTracker(check_interval=config.check_interval,
                            detection_mode=config.detection_mode)
    notifier = UsageNotifier()
    crash_handler = CrashHandler()

    # 启动管理 — 自动解析可执行路径
    _exe_path = _get_exe_path()
    import sys as _sys
    if getattr(_sys, 'frozen', False):
        # PyInstaller 打包后：_MEIPASS 上层就是 exe
        # 安全检测：若运行在 dist\ 目录下（非正式安装路径），禁用自启写入
        _install_dir = Path(_exe_path).parent
        _is_test_run = ('dist' in _install_dir.parts or
                        str(_install_dir).lower().startswith(
                            str(Path(__file__).resolve().parent.parent).lower()))
    else:
        # 开发模式：指向 src/main.py 的上层目录中的启动脚本（仅用于测试）
        _is_test_run = True  # 开发模式同样禁用自启
    startup = StartupManager(exe_path=_exe_path)
    if _is_test_run:
        logger.info('测试运行模式：跳过开机自启写入（exe 不在正式安装目录）')
    elif config.auto_start and not startup.is_startup_enabled():
        startup.enable_startup()

    # Bridge 通信（HTTP + 文件轮询）
    bridge = BridgeHandler()
    bridge.start_http_server(config_manager=config, data_store=data_store)
    bridge.start_polling(config_manager=config, data_store=data_store)

    # 自动保存定时器 — 记录每个 session 上次保存时的累计秒数，只写增量
    from src.constants import AUTO_SAVE_INTERVAL, MIN_AUTO_SAVE_DURATION

    _last_saved_dur: dict[int, float] = {}  # id(session) -> 上次已保存秒数

    def _save_session_data(session):
        """通用保存逻辑：计算增量并写入数据库"""
        try:
            cat = classifier.classify(
                session.name, session.window_title, session.exe_path)
            if cat == 'skip':
                return
            sid = id(session)
            prev = _last_saved_dur.get(sid, 0.0)
            delta = session.duration_seconds - prev
            if delta < 1:  # 不足1秒不写
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
            # 保存已结束的 session
            for session in tracker.sessions:
                if session.duration_seconds < MIN_AUTO_SAVE_DURATION:
                    continue
                _save_session_data(session)
            # 同时保存当前活跃 session（修复：原版遗漏导致崩溃时数据丢失）
            if tracker.current_session:
                tracker._update_current_duration()
                _save_session_data(tracker.current_session)

    save_thread = threading.Thread(target=_auto_save, daemon=True, name='auto-save')
    save_thread.start()

    # 通知回调 — 保存剩余增量 + 通知（不再 pop，防止 _auto_save 重复保存）
    def _on_session_end(old_session, new_session):
        try:
            if not old_session:
                return
            cat = classifier.classify(
                old_session.name, old_session.window_title, old_session.exe_path)
            # 所有非 skip 分类都保存数据（修复：原版跳过 'other' 导致数据丢失）
            if cat != 'skip' and old_session.duration_seconds >= MIN_AUTO_SAVE_DURATION:
                _save_session_data(old_session)
            if cat in ('skip', 'other'):
                return
            # 仅对 browser / game 做通知
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

    # 设置窗口回调 — 打开浏览器访问网页端设置
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

    def _on_quit():
        logger.info('正在退出...')
        # 退出前保存所有 pending 数据（修复：原版不保存导致退出时丢失当前 session）
        tracker._update_current_duration()
        if tracker.current_session:
            _save_session_data(tracker.current_session)
        for session in tracker.sessions:
            _save_session_data(session)
        tracker.stop()
        bridge.stop_polling()
        if tray_app:
            tray_app.stop()

    tray_app_obj = None
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

        # 启动追踪
        tracker.start()
        logger.info('UsageTracker 已启动')

        # 启动时检查更新
        if config.check_update:
            logger.info('启动更新检查...')
            from src.updater import check_update_async
            def _on_update_result(update_info):
                if update_info:
                    from src.i18n import t as _t
                    import tkinter as tk
                    from tkinter import messagebox
                    root = tk.Tk()
                    root.withdraw()
                    root.wm_attributes('-topmost', True)
                    msg = _t('updater.found', version=update_info['version'])
                    result = messagebox.askyesno(
                        _t('updater.title'), msg,
                        parent=root)
                    root.destroy()
                    if result:
                        import webbrowser
                        webbrowser.open(update_info['url'])
                else:
                    logger.debug('更新检查完成：已是最新版')
            check_update_async(VERSION, callback=_on_update_result)

        # 开机自动弹出昨日报告：仅当天第一次启动时弹出
        if config.auto_show_daily_report:
            today_str = datetime.now().date().isoformat()
            if config.last_report_shown_date != today_str:
                tray_app_obj._auto_open_daily = True
                config.last_report_shown_date = today_str
                config.save()

        # 运行托盘（阻塞）
        tray_app_obj.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error('主循环异常: %s', e)
        return 1

    logger.info('UsageTracker 已退出')
    return 0


def main():
    """入口函数（被 crash_handler 包装）"""
    return _run_app()


if __name__ == '__main__':
    # 崩溃恢复包装
    from src.crash_handler import CrashHandler
    CrashHandler().wrap(main)
