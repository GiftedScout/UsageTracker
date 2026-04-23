"""诊断脚本：纯命令行测试，不创建 GUI"""
import sys
import os
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print(f"Python: {sys.version}", flush=True)

# 1. 测试 i18n
try:
    from src.i18n import t, init as init_i18n
    init_i18n('zh-CN')
    print(f"i18n OK: t('settings.title') = {t('settings.title')!r}", flush=True)
except Exception as e:
    print(f"i18n FAIL: {e}", flush=True)
    traceback.print_exc()

# 2. 测试 settings_window import（不实例化）
try:
    from ui.settings_window import SettingsWindow
    print("settings_window import OK", flush=True)
except Exception as e:
    print(f"settings_window import FAIL: {e}", flush=True)
    traceback.print_exc()

# 3. 测试相对导入（tab_feedback 的关键问题）
try:
    from ui.tab_feedback import TabFeedback
    print("tab_feedback import OK", flush=True)
except Exception as e:
    print(f"tab_feedback import FAIL: {e}", flush=True)
    traceback.print_exc()

# 4. 测试所有 tab 文件
for tab_name in ['tab_general', 'tab_categories', 'tab_browsers', 'tab_games', 'tab_ignore', 'tab_database', 'tab_feedback']:
    try:
        mod = __import__(f'ui.{tab_name}', fromlist=[''])
        print(f"  {tab_name} OK", flush=True)
    except Exception as e:
        print(f"  {tab_name} FAIL: {e}", flush=True)

# 5. 测试打包模式下的相对导入
print("\n--- 打包模式模拟 ---", flush=True)
class FakeFrozen:
    frozen = True
sys.frozen = FakeFrozen()
sys.modules.pop('ui.tab_feedback', None)
sys.modules.pop('ui.settings_window', None)
try:
    from ui.tab_feedback import TabFeedback
    print("tab_feedback (frozen) import OK", flush=True)
except Exception as e:
    print(f"tab_feedback (frozen) import FAIL: {e}", flush=True)
    traceback.print_exc()

print("\nDONE", flush=True)
