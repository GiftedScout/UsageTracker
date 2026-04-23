"""诊断脚本：测试设置窗口能否在打包环境下打开"""
import sys
import os
import traceback

# 模拟打包环境
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print(f"Python: {sys.version}")
print(f"Path: {sys.path[:3]}")

try:
    print("\n1. Testing src.i18n import...")
    from src.i18n import t, init as init_i18n
    init_i18n('zh-CN')
    print(f"   OK - t('settings.title') = {t('settings.title')!r}")
except Exception as e:
    print(f"   FAIL: {e}")
    traceback.print_exc()

try:
    print("\n2. Testing ui.settings_window import...")
    from ui.settings_window import SettingsWindow
    print("   OK - SettingsWindow imported")
except Exception as e:
    print(f"   FAIL: {e}")
    traceback.print_exc()

try:
    print("\n3. Testing tk.Tk() + SettingsWindow creation...")
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    
    # Mock dependencies
    class MockConfig:
        theme = 'fairy_tale'
        data_retention = 'unlimited'
        language = 'zh-CN'
        auto_start = False
        auto_show_daily_report = True
        ignored_apps = []
        custom_categories = {}
        check_interval = 5
        privacy_accepted = True
        def save(self): pass
        def set(self, k, v): setattr(self, k, v)
        def get(self, k, default=None): return getattr(self, k, default)
        def remove_ignored_app(self, exe): pass

    class MockStartup:
        def is_startup_enabled(self): return False
        def enable_startup(self): pass
        def disable_startup(self): pass

    class MockClassifier:
        pass

    class MockDataStore:
        def get_database_size(self): return 0
        def cleanup_expired_data(self, policy): return 0
        def export_to_csv(self, *a): return 0
        def remove_ignored_app(self, exe): pass

    sw = SettingsWindow(
        root,
        config_manager=MockConfig(),
        startup_manager=MockStartup(),
        app_classifier=MockClassifier(),
        data_store=MockDataStore(),
        crash_handler=None,
    )
    print(f"   OK - SettingsWindow created, window title: {sw._window.title()!r}")
    
    # 立即销毁
    sw._window.destroy()
    root.destroy()
    print("   Window destroyed successfully")
except Exception as e:
    print(f"   FAIL: {e}")
    traceback.print_exc()

try:
    print("\n4. Testing i18n with t() call inside _get_tab_kwargs context...")
    from src.i18n import t
    # This simulates what happens during SettingsWindow._build()
    result = t('settings.general')
    print(f"   OK - t('settings.general') = {result!r}")
    result = t('settings.categories')
    print(f"   OK - t('settings.categories') = {result!r}")
    result = t('settings.feedback')
    print(f"   OK - t('settings.feedback') = {result!r}")
except Exception as e:
    print(f"   FAIL: {e}")
    traceback.print_exc()

print("\n=== All tests completed ===")
input("Press Enter to exit...")
