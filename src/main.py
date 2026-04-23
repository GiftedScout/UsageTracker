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
    """创建托盘图标（程序化生成 32x32 蓝色圆形图标）"""
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

    # 首次启动隐私声明
    config = _show_privacy_dialog()
    if config is None:
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
    from src.startup_manager import StartupManager
    from src.bridge_handler import BridgeHandler
    from src.crash_handler import CrashHandler

    # config 已由 _show_privacy_dialog() 返回，此处不重新实例化
    data_store = DataStore()
    data_store.cleanup_expired_data(config.data_retention)

    classifier = AppClassifier(config_manager=config)
    reporter = HTMLReportGenerator()
    reporter.set_data_store(data_store)
    tracker = UsageTracker(check_interval=config.check_interval)
    notifier = UsageNotifier()
    crash_handler = CrashHandler()

    # 启动管理 — 自动解析可执行路径
    import sys as _sys
    if getattr(_sys, 'frozen', False):
        # PyInstaller 打包后：_MEIPASS 上层就是 exe
        _exe_path = _sys.executable
    else:
        # 开发模式：指向 src/main.py 的上层目录中的启动脚本（仅用于测试）
        _exe_path = str(Path(__file__).resolve().parent.parent / 'UsageTracker.exe')
    startup = StartupManager(exe_path=_exe_path)
    if config.auto_start and not startup.is_startup_enabled():
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

    tracker.on_app_switch = _on_session_end

    # 设置窗口回调 — 独立线程运行 mainloop，防止重复打开
    _settings_lock = threading.Lock()

    def _open_settings():
        logger.info('设置窗口：_open_settings 被调用')
        if not _settings_lock.acquire(blocking=False):
            logger.info('设置窗口：已有实例，忽略')
            return  # 已有设置窗口打开，忽略重复点击
        def _run():
            try:
                logger.info('设置窗口：开始创建...')
                import tkinter as tk
                logger.info('设置窗口：tkinter 导入成功')
                from ui.settings_window import SettingsWindow
                logger.info('设置窗口：SettingsWindow 导入成功')
                # 用独立 Tk 根（设为实际可见的隐形小窗，作为 Toplevel 的 parent）
                settings_root = tk.Tk()
                settings_root.withdraw()          # 隐藏根窗口本体
                settings_root.wm_attributes('-alpha', 0)  # 完全透明
                settings_root.wm_attributes('-topmost', True)
                logger.info('设置窗口：Tk 根窗口创建成功')

                sw = SettingsWindow(
                    settings_root, config_manager=config,
                    startup_manager=startup, app_classifier=classifier,
                    data_store=data_store, crash_handler=crash_handler)
                logger.info('设置窗口：SettingsWindow 实例化成功')

                # 窗口关闭时销毁整个 Tk 根，退出 mainloop（必须用 after 确保在主循环内执行）
                def _destroy():
                    try:
                        settings_root.destroy()
                    except Exception:
                        pass

                orig_ok = sw._on_ok
                orig_cancel = sw._on_cancel

                def _on_close_ok():
                    orig_ok()
                    settings_root.after(0, _destroy)

                def _on_close_cancel():
                    orig_cancel()
                    settings_root.after(0, _destroy)

                sw._window.protocol('WM_DELETE_WINDOW', _on_close_cancel)
                sw._on_ok = _on_close_ok
                sw._on_cancel = _on_close_cancel

                # 居中显示
                sw._window.update_idletasks()
                w, h = 700, 500
                x = (sw._window.winfo_screenwidth() - w) // 2
                y = (sw._window.winfo_screenheight() - h) // 2
                sw._window.geometry(f'{w}x{h}+{x}+{y}')
                sw._window.deiconify()
                sw._window.lift()
                sw._window.focus_force()
                logger.info('设置窗口：窗口已显示，进入 mainloop')
                settings_root.mainloop()
                logger.info('设置窗口：mainloop 退出')
            except Exception as exc:
                logger.error('设置窗口异常: %s', exc, exc_info=True)
            finally:
                _settings_lock.release()

        # 注意：局部变量名改为 _thr，避免覆盖 i18n 的 t() 函数
        _thr = threading.Thread(target=_run, daemon=True, name='settings-window')
        _thr.start()

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

        # 开机自动弹出昨日报告（在托盘就绪后触发，不再用固定延迟）
        if config.auto_show_daily_report:
            tray_app_obj._auto_open_daily = True

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
