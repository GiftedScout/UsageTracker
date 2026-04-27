# UsageTracker v0.1.2 路线图

> **创建日期**: 2026-04-24  
> **状态**: Phase 1 + Phase 2 已完成，Phase 3 测试发版待进行  
> **前置版本**: v0.1.1

---

## 概述

v0.1.2 是 v0.1.1 的修复增强版本，聚焦以下目标：

1. **修复忽略名单逻辑缺陷** — 路径匹配失效导致忽略功能不生效
2. **修复 i18n 显示原始 key** — 主题/保留策略下拉框显示英文 key 而非中文译文
3. **关于菜单可交互化** — 从灰色不可点改为点击后显示版本更新日志弹窗
4. **新增进程选择器** — 从当前运行进程中选择，快速添加到分类/游戏目录/忽略名单

---

## 一、Bug 修复

### 1.1 忽略名单路径匹配失效

**问题描述**：从日报点击忽略按钮后，应用仍被正常追踪和记录，忽略功能未生效。

**根因分析**：

| # | 问题 | 位置 | 影响 |
|:--|:-----|:-----|:-----|
| A | `os.path.realpath()` 破坏路径一致性 | `bridge_handler.py:39` | Bridge 收到路径后经 `realpath` 规范化（解析符号链接、统一大小写等），但运行时 `psutil.Process().exe()` 返回原始路径。两者格式不一致导致精确匹配失败 |
| B | 大小写敏感匹配 | `config_manager.py:183,198,206` | `add_ignored_app`、`remove_ignored_app`、`is_ignored` 均使用 `==` 精确比较。Windows 路径不区分大小写，`D:\App\Game.exe` ≠ `d:\app\game.exe` |
| C | except 块二次写入失败 | `bridge_handler.py:115-117` | 如果第一次 `_respond` 因连接断开失败，except 块再次调用 `_respond(500, ...)` 也会抛 `BrokenPipeError` |

**修复方案**：

| 修改 | 文件 | 内容 |
|:-----|:-----|:-----|
| 去掉 `realpath` | `bridge_handler.py` | `_handle_ignore` 中直接使用原始 `exe_path`，不做路径转换 |
| except 安全处理 | `bridge_handler.py` | `_handle_ignore` 的 except 块中不再二次调用 `_respond`，仅记日志 |
| 大小写不敏感匹配 | `config_manager.py` | `add_ignored_app`、`remove_ignored_app`、`is_ignored` 统一用 `.lower()` 比较 |
| 大小写不敏感分类 | `app_classifier.py` | `classify()` 和 `should_skip()` 中的忽略匹配也用 `.lower()` |

### 1.2 i18n 翻译未完整映射（下拉框显示原始 key）

**问题描述**：设置界面的"主题风格"和"数据保留"下拉框显示的是英文 key（如 `fairy_tale`、`unlimited`），而非翻译后的中文（如"童话"、"不限制"）。

**根因分析**：

`tab_general.py` 中，下拉框的 `values` 直接写死了英文 key 作为选项值，Combobox 显示的就是存储值本身，没有做"存储 key → 显示译文"的映射：

```python
# 现状（错误）：values 是英文 key，用户看到 fairy_tale / unlimited
values=[v for _, v in THEMES]   # THEMES = [('minimal','minimal'), ('fairy_tale','fairy_tale'), ...]
values=['unlimited', '1year', '3months', '1month']
```

**修复方案**：

使用"显示列表 + 存储映射"分离的模式：

| 修改 | 文件 | 内容 |
|:-----|:-----|:-----|
| 主题下拉框 | `ui/tab_general.py` | Combobox 显示 `t('theme.minimal')` 等译文，`apply()` 时反向映射回 key |
| 保留策略下拉框 | `ui/tab_general.py` | Combobox 显示 `t('retention.unlimited')` 等译文，`apply()` 时反向映射回 key |
| 初始值回显 | `ui/tab_general.py` | 构造时将 `config.theme`（英文 key）翻译成对应的中文显示值填入 Combobox |

> 语言下拉框（`zh-CN` / `en`）不需要修改，它的值本身就是展示值，不需要二次翻译。

---

### 1.3 托盘"关于"菜单灰色不可点击

**问题描述**：右键托盘菜单的"关于 (v0.1.x)"选项为灰色（`enabled=False`），无法点击，用户无法查看版本说明。

**根因分析**：

`tray_app.py` 第 48、124-125 行：
```python
pystray.MenuItem(f'{t("tray.about")} ({VERSION})', self._show_about, enabled=False)

def _show_about(self, icon=None, item=None) -> None:
    pass  # enabled=False，不可点击
```

`_show_about` 是空函数，且菜单项本身被禁用。

**修复方案**：

1. **菜单项改为可点击**：去掉 `enabled=False`
2. **`_show_about` 实现弹窗**：弹出 tkinter `Toplevel` 窗口，显示当前版本的更新日志内容
3. **更新日志内容打包时内置**：`release-notes.md` 已在仓库根目录，打包时随 `_MEIPASS` 一起打入（spec 里加入 datas），运行时读取对应版本段落
4. **底部链接到 GitHub**：弹窗下方增加"查看完整更新历史"超链接，点击用 `webbrowser.open()` 打开 GitHub Releases 页面（需要网络，但不预存）

**实现细节**：

- 弹窗尺寸约 480×340，居中，不可改大小
- 顶部显示：`UsageTracker v0.1.x`（大字）
- 内容区：当前版本 release notes 的纯文本（从打包进去的 release-notes.md 或硬编码常量中读取）
- 底部按钮行：`[ 查看 GitHub 主页 ]`  `[ 关闭 ]`
- "查看 GitHub 主页"调用 `webbrowser.open('https://github.com/GiftedScout/UsageTracker')`

**涉及文件**：

| 文件 | 修改 |
|:-----|:-----|
| `src/tray_app.py` | 菜单项去 `enabled=False`；实现 `_show_about` 弹窗逻辑 |
| `src/version.py` | 新增 `RELEASE_NOTES` 常量（当前版本的更新内容字符串，打包时固定） |
| `UsageTracker.spec` | 确认 `release-notes.md` 不需要单独打包（改用常量方式则不需要） |

---

## 二、新增功能

### 2.1 进程选择器

**背景**：当前添加分类、游戏、忽略名单时，需要手动输入进程名或路径，用户不知道应该填什么。

**目标**：从当前运行的进程中直接选择，快速添加到对应的分类列表。

#### 功能设计

1. **触发入口**：分类管理、游戏目录、忽略名单的"添加"按钮旁新增"从进程选择"按钮
2. **进程列表弹窗**：点击后弹出窗口，显示当前所有正在运行的进程列表（进程名 + 完整路径）
3. **筛选搜索**：支持按进程名/路径实时筛选
4. **多选支持**：可同时选中多个进程，一键批量添加
5. **一键添加**：选中进程后，点击"添加"按钮，自动填充到当前管理列表

#### 实现要点

- 使用 `psutil.process_iter(['pid', 'name', 'exe'])` 获取当前进程列表
- 弹窗为独立 `Toplevel` 窗口，居中显示
- 进程列表显示列：`进程名` | `路径` | `PID`
- 排序：按进程名字母排序
- 对已添加的进程做标记/置灰（避免重复添加）
- 需要处理的边界情况：
  - 系统进程（`System`、`Idle`）无 `exe` 路径 → 过滤或标记为"系统进程"
  - 64 位系统下的 32 位进程路径在 `SysWOW64` → 正常显示即可
  - 进程列表获取时可能抛 `psutil.AccessDenied` → try-except 单条跳过

#### 涉及文件

| 文件 | 修改 |
|:-----|:-----|
| 新增 `ui/process_picker.py` | 进程选择器弹窗组件 |
| `ui/tab_categories.py` | 分类管理 tab 增加"从进程选择"按钮 |
| `ui/tab_games.py` | 游戏目录 tab 增加"从进程选择"按钮 |
| `ui/tab_ignore.py` | 忽略名单 tab 增加"从进程选择"按钮 |
| `locales/zh-CN.json` | 新增进程选择器相关翻译 key |
| `locales/en.json` | 新增进程选择器相关翻译 key |

---

## 三、已知问题收集（待后续版本处理）

> 以下问题在开发/测试中发现，记录在此待分配版本。

| # | 问题 | 严重性 | 来源 | 状态 |
|:--|:-----|:-------|:-----|:-----|
| 1 | ~~旧数据（v0 迁移前）无 `exe_path`，日报忽略按钮发送空路径 → Bridge 返回 400~~ | ~~低~~ | ~~v0.1.2 分析~~ | ✅ 已修复（v0.1.2） |
| 2 | ~~忽略只影响未来数据，已记录的历史数据不会被清除或隐藏~~ | ~~低~~ | ~~用户反馈~~ | ✅ 已修复（v0.1.2） |
| 3 | ~~游戏目录提示"只需填写进程名"可能让用户困惑（忽略名单需要完整路径，两者不一致）~~ | ~~低~~ | ~~v0.1.2 分析~~ | ✅ 已修复（v0.1.2） |
| 4 | ~~新增分类后添加程序导致界面卡死~~ | ~~中~~ | ~~用户反馈~~ | ✅ 已修复（v0.1.2） |
| 5 | ~~开机自动弹报告触发频率过高（每次启动都弹）~~ | ~~中~~ | ~~用户反馈~~ | ✅ 已修复（v0.1.2） |

---

## 四、功能需求收集（待后续版本处理）

> 新增功能想法，记录在此待评估和分配版本。

| # | 功能 | 描述 | 来源 | 状态 |
|:--|:-----|:-----|:-----|:-----|
| 1 | — | — | — | — |

---

## 五、实施顺序

```
Phase 1: Bug 修复 ✅ 已完成
  ├─ bridge_handler.py — 去掉 realpath + except 安全处理
  ├─ config_manager.py — 忽略名单大小写不敏感 + last_report_shown_date 属性
  ├─ app_classifier.py — 分类时忽略匹配大小写不敏感（已内置 .lower()，无需另改）
  ├─ ui/tab_general.py — 主题/保留策略下拉框显示翻译文本
  ├─ ui/tab_categories.py — _on_cat_select / _remove_category Treeview.delete 修复（卡死）
  ├─ src/tray_app.py + src/version.py — 关于弹窗实现
  └─ src/main.py + src/config_manager.py — 弹报告仅当天首次触发

Phase 2: 进程选择器 ✅ 已完成
  ├─ 新建 ui/process_picker.py — 进程列表弹窗组件（搜索过滤 + 后台加载）
  ├─ ui/tab_categories.py — "从进程选择"按钮（返回完整 exe 路径）
  ├─ ui/tab_games.py — "从进程选择"预填 exe 名 + 游戏名（exe_only 模式）
  ├─ ui/tab_ignore.py — "从进程添加"直接写入忽略名单
  └─ locales/zh-CN.json + en.json — 新增 process_picker.* 翻译 key

Phase 3: 测试 + 发版
  ├─ 手动测试忽略名单完整流程
  ├─ 手动测试进程选择器三个入口
  ├─ 手动测试主题/保留策略下拉框中文显示
  ├─ 手动测试"关于"弹窗（版本号、更新日志、GitHub 链接）
  ├─ 手动测试分类添加程序（不再卡死）
  ├─ 手动测试多次启动不重复弹报告
  └─ 版本号更新 → commit → tag → 打包 → release
```

---

## 六、版本号策略

本次更新发布为 **v0.1.2**（小版本修复增强）。

**Release Notes 草案**：

```
## UsageTracker v0.1.2

修复与增强更新。

### 修复内容
| 问题 | 说明 |
|:-----|:-----|
| 忽略名单不生效 | 修复路径匹配逻辑，忽略功能现已正常工作 |
| 设置界面主题/保留策略显示英文 key | 下拉框现在正确显示中文译文（童话、不限制等） |

### 新增功能
| 功能 | 说明 |
|:-----|:-----|
| 进程选择器 | 分类管理、游戏目录、忽略名单支持从当前运行进程中选择添加 |
| 关于弹窗 | 托盘右键"关于"菜单现可点击，显示当前版本更新日志及 GitHub 主页链接 |

### 升级说明
直接运行新安装程序覆盖安装即可，数据会自动保留。
```
