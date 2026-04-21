# UsageTracker v0.1.0 版本更新计划

> **创建日期**: 2026-04-18  
> **状态**: 已完成  
> **前置版本**: v0.1.0-beta

---

## 概述

v0.1.0 是 v0.1.0-beta 发布后的首个正式版本，聚焦两个核心任务：

1. **修复开机自启 Bug** — 用户测试反馈的设置界面问题
2. **中英双语支持** — README、安装程序、设置界面、日报内容全面双语化

---

## 一、修复开机自启 Bug

### 1.1 问题分析

**文件**: `ui/tab_general.py` 第 48-87 行

| 问题 | 描述 | 严重性 |
|:---|:---|:---|
| 重复执行 | `_toggle_auto_start()` 绑定到 Checkbutton command（勾选时立即执行），`apply()` 又调用一次（点确定/应用时再执行），每次操作被执行两遍 | 高 |
| 取消无效 | 勾选框立即执行 `config.save()` + 快捷方式操作，点"取消"只关闭窗口不恢复配置 | 高 |
| 状态不同步 | 勾选框初始值只读 `config.auto_start`，不检查 `startup_manager.is_startup_enabled()`，配置与实际快捷方式可能不一致 | 中 |

### 1.2 修复方案

**核心原则：延迟提交，UI 与操作分离**

1. **勾选框只改 UI 状态**：移除 `command=self._toggle_auto_start`，勾选框不再立即触发任何操作
2. **`apply()` 统一提交**：所有变更（主题、保留策略、自启）都在 `apply()` 中一次性提交
3. **初始值双向同步**：构造函数中同时检查 `config.auto_start` 和 `startup_manager.is_startup_enabled()`，取 OR 值
4. **移除 `_toggle_auto_start()` 独立方法**：逻辑合并进 `apply()`

**修改文件**：`ui/tab_general.py`

```python
# 修改前（问题代码）
self._auto_start_var = tk.BooleanVar(value=self._config.auto_start)
ttk.Checkbutton(self, text='开机自动启动', variable=self._auto_start_var,
                command=self._toggle_auto_start).grid(...)

# 修改后（修复代码）
# 初始值：配置或快捷方式存在即为 True
startup_enabled = self._config.auto_start or self._startup.is_startup_enabled()
self._auto_start_var = tk.BooleanVar(value=startup_enabled)
ttk.Checkbutton(self, text='开机自动启动', variable=self._auto_start_var).grid(...)
# 移除 command 回调

# apply() 中统一处理
def apply(self):
    self._config.theme = self._theme_var.get()
    self._config.data_retention = self._retention_var.get()
    self._config.auto_start = self._auto_start_var.get()
    self._config.save()
    if self._auto_start_var.get():
        self._startup.enable_startup()
    else:
        self._startup.disable_startup()
```

---

## 二、中英双语支持

### 2.1 总体设计

#### 双语范围

| 组件 | 双语方案 | 说明 |
|:---|:---|:---|
| **README** | 两个独立文件 + 切换链接 | `README.md`（英文默认）+ `README.zh-CN.md`（中文），顶部互相链接 |
| **安装程序（Inno Setup）** | 安装界面多语言 + 安装后语言固定 | Inno Setup 原生支持多语言 UI；安装时选择语言后写入 `config.json` 的 `language` 字段，程序运行时读取该配置 |
| **设置界面（tkinter）** | i18n 模块 + 语言文件 | 所有 UI 文案通过翻译函数获取，运行时根据 config.language 选择 |
| **日报内容（HTML 报告）** | reporter.py 注入对应语言文案 | 报告 HTML 中的标题、分类名、图表标签根据当前语言配置注入 |
| **托盘菜单** | tray_app.py 使用翻译函数 | 菜单项文本、tooltip 等根据语言配置显示 |

#### 语言切换时机

- **安装时**：Inno Setup 语言选择对话框 → 选定语言 → 写入 config.json → 安装完成后程序即使用选定语言
- **运行时**：设置界面"通用设置"中增加"语言"下拉框 → 切换后立即生效（重新加载翻译、刷新托盘菜单）
- **默认值**：首次运行（无 config.json）时根据系统语言自动选择

### 2.2 README 双语方案

#### 文件结构

```
README.md            # 英文版（GitHub 默认显示）
README.zh-CN.md      # 中文版
```

#### 切换机制

两个文件顶部互相链接：

**README.md 顶部**：
```html
<p align="right">
  <a href="README.zh-CN.md">中文</a> | English
</p>
```

**README.zh-CN.md 顶部**：
```html
<p align="right">
  中文 | <a href="README.md">English</a>
</p>
```

#### Git 切换策略

- 两个文件独立存在，不存在"切换"概念
- GitHub 默认显示 `README.md`（英文），中文用户点击链接查看中文版
- 可在 `.github/` 中配置 `DEFAULT_BRANCH` 的 README 渲染语言偏好（GitHub 暂不支持此特性）
- 替代方案：通过 GitHub Actions 在不同分支维护不同默认 README（暂不实现，复杂度过高）

### 2.3 安装程序多语言

#### Inno Setup 语言选择

**方案**：Inno Setup 原生支持 `[Languages]` 节，安装界面自动显示语言选择对话框。

```iss
[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Setup]
ShowLanguageDialog=yes
```

**安装后语言固定**：

安装程序在用户选择语言后，将语言代码写入配置文件：

```iss
[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  LangCode: string;
begin
  if CurStep = ssPostInstall then
  begin
    // 根据用户选择的语言写入配置
    if ActiveLanguage = 'chinesesimplified' then
      LangCode := 'zh-CN'
    else
      LangCode := 'en';
    // 写入 {app}\config\config.json 的 language 字段
    SaveStringToFile(ExpandConstant('{app}\config\config.json'), LangCode, False);
  end;
end;
```

> **注意**：需要处理首次安装（无 config.json）和升级安装（已有 config.json）两种情况。首次安装时创建默认配置文件并写入语言；升级安装时只修改 language 字段。

### 2.4 国际化模块（i18n）

#### 文件结构

```
src/
  i18n.py              # 翻译管理器
locales/
  zh_CN.json           # 中文翻译
  en.json              # 英文翻译
```

#### i18n.py 设计

```python
"""轻量国际化模块 — JSON 翻译文件 + 运行时切换"""

import json
from pathlib import Path

_LOCALE_DIR = Path(__file__).parent.parent / 'locales'
_current_lang = 'zh-CN'
_translations = {}

def init(language: str = 'zh-CN'):
    """加载指定语言的翻译文件"""
    global _current_lang, _translations
    _current_lang = language
    locale_file = _LOCALE_DIR / f'{language}.json'
    if locale_file.exists():
        with open(locale_file, 'r', encoding='utf-8') as f:
            _translations = json.load(f)

def t(key: str, **kwargs) -> str:
    """翻译函数：根据 key 获取翻译文本，支持 format 占位符"""
    text = _translations.get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text

def get_language() -> str:
    return _current_lang
```

#### 翻译文件示例

**locales/zh_CN.json**：
```json
{
  "app_name": "UsageTracker",
  "tray.yesterday_report": "昨日日报",
  "tray.last_week_report": "上周周报",
  "tray.last_month_report": "上月月报",
  "tray.settings": "设置",
  "tray.about": "关于",
  "tray.exit": "退出",
  "settings.title": "UsageTracker 设置",
  "settings.general": "通用设置",
  "settings.categories": "分类管理",
  "settings.browsers": "浏览器管理",
  "settings.games": "游戏目录",
  "settings.ignore": "忽略名单",
  "settings.database": "数据库管理",
  "settings.feedback": "运行日志与反馈",
  "settings.ok": "确定",
  "settings.cancel": "取消",
  "settings.apply": "应用",
  "general.theme": "主题风格",
  "general.retention": "数据保留",
  "general.auto_start": "开机自动启动",
  "general.language": "语言",
  "general.privacy": "隐私声明",
  "general.version": "版本",
  "general.privacy_text": "所有数据仅存储在本地设备，不会联网上传。\n数据库和配置文件位于安装目录下。",
  "theme.minimal": "简约",
  "theme.fairy_tale": "童话",
  "theme.business": "商务",
  "retention.unlimited": "不限制",
  "retention.1year": "1年",
  "retention.3months": "3个月",
  "retention.1month": "1个月",
  "report.daily_title": "{date} 使用时长报告",
  "report.yesterday_title": "昨日时光记录",
  "report.weekly_title": "周使用时长报告",
  "report.monthly_title": "月使用时长报告",
  "report.category_browser": "浏览器",
  "report.category_game": "游戏",
  "report.category_other": "其他",
  "report.total_time": "总使用时长",
  "report.top_apps": "应用排行",
  "report.game_time": "游戏时长对比",
  "notifier.browser_timeout": "浏览器已使用 {time}，注意休息！",
  "notifier.game_timeout": "游戏已使用 {time}，注意休息！"
}
```

**locales/en.json**：
```json
{
  "app_name": "UsageTracker",
  "tray.yesterday_report": "Yesterday's Report",
  "tray.last_week_report": "Last Week Report",
  "tray.last_month_report": "Last Month Report",
  "tray.settings": "Settings",
  "tray.about": "About",
  "tray.exit": "Exit",
  "settings.title": "UsageTracker Settings",
  "settings.general": "General",
  "settings.categories": "Categories",
  "settings.browsers": "Browsers",
  "settings.games": "Games",
  "settings.ignore": "Ignore List",
  "settings.database": "Database",
  "settings.feedback": "Logs & Feedback",
  "settings.ok": "OK",
  "settings.cancel": "Cancel",
  "settings.apply": "Apply",
  "general.theme": "Theme",
  "general.retention": "Data Retention",
  "general.auto_start": "Auto-start on Boot",
  "general.language": "Language",
  "general.privacy": "Privacy Policy",
  "general.version": "Version",
  "general.privacy_text": "All data is stored locally on your device.\nNo network connections or uploads.",
  "theme.minimal": "Minimal",
  "theme.fairy_tale": "Fairy Tale",
  "theme.business": "Business",
  "retention.unlimited": "Unlimited",
  "retention.1year": "1 Year",
  "retention.3months": "3 Months",
  "retention.1month": "1 Month",
  "report.daily_title": "Usage Report - {date}",
  "report.yesterday_title": "Yesterday's Usage",
  "report.weekly_title": "Weekly Usage Report",
  "report.monthly_title": "Monthly Usage Report",
  "report.category_browser": "Browsers",
  "report.category_game": "Games",
  "report.category_other": "Others",
  "report.total_time": "Total Usage",
  "report.top_apps": "Top Applications",
  "report.game_time": "Game Time Comparison",
  "notifier.browser_timeout": "Browser used for {time}, take a break!",
  "notifier.game_timeout": "Game used for {time}, take a break!"
}
```

### 2.5 设置界面国际化

#### 涉及文件

| 文件 | 修改内容 |
|:---|:---|
| `ui/settings_window.py` | 窗口标题、标签页名称、按钮文本 |
| `ui/tab_general.py` | 主题名、保留策略名、勾选框文本、隐私声明 |
| `ui/tab_categories.py` | 标签页内所有按钮、列表头、提示文本 |
| `ui/tab_browsers.py` | 标签页内所有按钮、列表头 |
| `ui/tab_games.py` | 标签页内所有按钮、列表头 |
| `ui/tab_ignore.py` | 标签页内所有按钮、列表头 |
| `ui/tab_database.py` | 标签页内所有按钮、提示文本 |
| `ui/tab_feedback.py` | 标签页内所有按钮、列表头、日志文本 |

#### 使用方式

```python
from src.i18n import t

# 修改前
ttk.Label(self, text='主题风格:').grid(...)

# 修改后
ttk.Label(self, text=t('general.theme')).grid(...)
```

#### 语言切换

`tab_general.py` 增加语言下拉框：

```python
LANGUAGES = [('中文', 'zh-CN'), ('English', 'en')]

ttk.Label(self, text=t('general.language')).grid(row=row, column=0, **pad)
self._lang_var = tk.StringVar(value=_current_lang)
lang_combo = ttk.Combobox(self, textvariable=self._lang_var,
                          values=[v for _, v in LANGUAGES], state='readonly', width=16)
lang_combo.grid(row=row, column=1, **pad)
lang_combo.bind('<<ComboboxSelected>>', self._on_language_change)
```

切换语言后：
1. 调用 `i18n.init(new_lang)` 重新加载翻译
2. 写入 `config.language`
3. 刷新托盘菜单
4. 弹出提示"语言已切换，重启后生效"

### 2.6 核心模块国际化

#### tray_app.py

```python
# 修改前
menu_items = [
    MenuItem('昨日日报', callback=...),
    MenuItem('上周周报', callback=...),
    MenuItem('设置', callback=...),
    MenuItem('退出', callback=...),
]

# 修改后
menu_items = [
    MenuItem(t('tray.yesterday_report'), callback=...),
    MenuItem(t('tray.last_week_report'), callback=...),
    MenuItem(t('tray.settings'), callback=...),
    MenuItem(t('tray.exit'), callback=...),
]
```

#### reporter.py

日报/周报/月报中的所有硬编码中文文案替换为 `t()` 调用：

```python
# 修改前
title = f'{date_str} 使用时长报告'

# 修改后
title = t('report.daily_title', date=date_str)
```

分类名也走翻译：
```python
# 修改前
CATEGORY_NAMES = {'browser': '浏览器', 'game': '游戏', 'other': '其他'}

# 修改后
def get_category_name(key):
    return t(f'report.category_{key}')
```

#### notifier.py

通知消息双语化：
```python
# 修改前
message = f'浏览器已使用 {time_str}，注意休息！'

# 修改后
message = t('notifier.browser_timeout', time=time_str)
```

### 2.7 PyInstaller 打包适配

**UsageTracker.spec** 需要新增 locales 目录到打包数据：

```python
datas += [
    ('locales/*.json', 'locales'),
]
```

### 2.8 config_manager.py 适配

新增 `language` 配置项：

```python
DEFAULT_CONFIG = {
    ...
    'language': 'zh-CN',  # 新增
}

@property
def language(self) -> str:
    return self._config.get('language', 'zh-CN')

@language.setter
def language(self, value: str):
    if value in ('zh-CN', 'en'):
        self._config['language'] = value
```

### 2.9 main.py 启动流程适配

```python
# 在初始化配置后加载翻译
from src.i18n import init as init_i18n
init_i18n(config_manager.language)
```

---

## 三、实施顺序

```
Phase 1: Bug 修复
  └─ 修复开机自启 Bug（ui/tab_general.py）

Phase 2: i18n 基础设施
  ├─ 创建 src/i18n.py
  ├─ 创建 locales/zh_CN.json + locales/en.json
  ├─ config_manager.py 增加 language 字段
  └─ main.py 启动时初始化 i18n

Phase 3: UI 国际化
  ├─ ui/settings_window.py（窗口标题、标签名、按钮）
  ├─ ui/tab_general.py（所有文案 + 语言切换下拉框）
  ├─ ui/tab_categories.py
  ├─ ui/tab_browsers.py
  ├─ ui/tab_games.py
  ├─ ui/tab_ignore.py
  ├─ ui/tab_database.py
  └─ ui/tab_feedback.py

Phase 4: 核心模块国际化
  ├─ src/tray_app.py（菜单文本、tooltip）
  ├─ src/reporter.py（报告标题、分类名、图表标签）
  └─ src/notifier.py（通知消息）

Phase 5: 安装程序 + README
  ├─ installer.iss 多语言支持 + 配置写入
  └─ README.md（英文）+ README.zh-CN.md（中文）

Phase 6: 打包验证
  ├─ UsageTracker.spec 更新
  └─ 重新打包 + 安装测试
```

---

## 四、风险与注意事项

| 风险 | 应对措施 |
|:---|:---|
| Inno Setup 7 预览版可能无 ChineseSimplified.isl | 回退到使用 Default.isl，仅安装界面用英文，但安装下来的程序语言由配置控制 |
| 翻译 key 遗漏导致显示 key 原文 | `t()` 函数在 key 不存在时返回 key 本身（而非报错），方便排查遗漏 |
| 语言切换后托盘菜单不刷新 | 语言切换时重建托盘图标和菜单 |
| 升级安装时 config.json 被覆盖 | Inno Setup Code 段使用 JSON 解析只修改 language 字段，不覆盖整个文件 |

---

## 五、版本号策略

本次更新发布为 **v0.1.0**（首个正式版，从 v0.1.0-beta 去掉预发布后缀）。从 roadmap 视角，原计划在 v0.2.0-beta 才做的 i18n 提前到了 v0.1.0。

**开源许可证**：GPL-3.0（允许学习和修改，衍生作品必须同样开源，禁止闭源商用）。
