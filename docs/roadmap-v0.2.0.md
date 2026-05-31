# UsageTracker v0.2.0 版本规划

> **创建日期**: 2026-04-27  
> **状态**: 规划中  
> **前置版本**: v0.1.2  
> **预估发布**: 2026 年 Q2

---

## 概述

v0.2.0 聚焦**视觉升级**、**智能化增强**和**体验优化**三大方向：

1. **GitHub 项目视觉升级** — 图标、封面、QQ 群入口，让项目页面更专业
2. **设置界面 UI 升级** — 参考封面设计风格的精美模式 + 安装引导，保留精简模式可切换
3. **事件驱动追踪** — 替代 5 秒轮询，零延迟检测窗口切换
4. **自动更新** — 启动检查新版本，托盘通知 + 手动下载
5. **报告增强** — 趋势对比、自定义时间范围、PDF 导出
6. **分类系统增强** — 自动分类建议、浏览器子分类
7. **性能优化** — 数据库优化、内存/启动优化
8. **安装体验优化** — 静默安装、便携版

---

## 一、GitHub 项目视觉升级

### 1.1 README 图标和封面

**状态**: ✅ 文件已准备，待 v0.2.0 一起提交

- `assets/logo.png` — 应用图标（已放入仓库）
- `assets/banner.png` — 封面横幅（已放入仓库）
- README.md 标题旁展示 logo，顶部展示封面
- README.zh-CN.md 同步更新

### 1.2 QQ 群交流入口

**状态**: ✅ 文案已写好，待 v0.2.0 一起提交

- 两个 README 底部新增"社区交流"板块
- QQ 群号：747117152

### 1.3 GitHub Social Preview

- 配置 `assets/logo.png` 为 GitHub Social Image（Open Graph）
- 在仓库设置中指定项目 Logo，让 GitHub 摘要卡片显示图标

---

## 二、设置界面 UI 升级

### 2.1 背景与设计方向

**现状**：v0.1.x 设置界面采用原生 tkinter 控件，风格极简但缺乏视觉层次感，对新用户不够友好。

**v0.2.0 方向**：
- 提供两套界面模式，用户可随时切换：
  - **精简模式**（保留）：当前 tkinter 原生控件，启动快、内存占用低
  - **精美模式**（新增）：参考 `assets/banner.png` 封面设计风格，作为**安装后首次打开引导界面的默认风格**
- 两套模式共用同一套 `ConfigManager`，仅 UI 层不同

### 2.2 精美模式界面规范

**风格参照**：`assets/banner.png`

#### 2.2.1 配色体系（基于 baner.png 视觉分析提取）

| 颜色 | 色值 | 用途 |
|------|------|------|
| 主背景深色 | `#0a0f1a` | 窗口整体背景（深海军蓝） |
| 背景渐变色 | `#0a0f1a` → `#141b2d` | 窗口背景径向渐变 |
| 侧边栏背景 | `#0d1520` | 左侧 Tab 导航面板底色 |
| 内容卡片背景 | `#1a2332` | 右侧设置内容区域的卡片底色 |
| 选中高亮 | `#1E90FF` (亮蓝) | 侧边栏当前 Tab 选中状态 |
| 高亮发光 | `#1E90FF` (透明度 30%) | 选中项外围发光效果 |
| 强调色 | `#00CED1` (青绿) | 图表/装饰元素 |
| 主文字 | `#FFFFFF` | 标题、重要标签 |
| 辅助文字 | `#b0b8c8` | 描述、次要信息 |
| 按钮主色 | `#1E90FF` | 确定/应用等主要操作按钮 |
| 按钮次色 | `#3a4a5c` | 取消按钮、次要操作 |
| 输入框背景 | `#1e2a3a` | 下拉框、输入框底色 |
| 边框 | `#2a3a4e` | 卡片/输入框边框 |

#### 2.2.2 布局结构（左 Tab 侧栏 + 右内容区）

```
╔═══════════════════════════════════════════════════════════════╗
║           窗口背景: #0a0f1a → #141b2d 径向渐变              ║
║                                                               ║
║   ┌────────────┬────────────────────────────────────────┐    ║
║   │ 侧边栏      │ 内容区　　　　　　　　　　           │    ║
║   │ #0d1520    │ #1a2332（卡片）　　　　　　　　　　   │    ║
║   │             │                                        │    ║
║   │ [●] 通用   │  ┌──────────────────────────────────┐  │    ║
║   │ [ ] 分类   │  │ 🖥️ UsageTracker v0.2.0          │  │    ║
║   │ [ ] 浏览器 │  │  版本: v0.2.0                    │  │    ║
║   │ [ ] 游戏   │  │  语言: 中文                      │  │    ║
║   │ [ ] 忽略   │  │  许可: GPL-3.0                  │  │    ║
║   │ [ ] 数据库 │  └──────────────────────────────────┘  │    ║
║   │ [ ] 反馈   │                                        │    ║
║   │             │  ┌─ 基本设置 ─────────────────────┐   │    ║
║   │             │  │  语言 [中文 ▼]  开机自启 [●]  │   │    ║
║   │             │  │  自动报告 [●]                  │   │    ║
║   │             │  └───────────────────────────────┘   │    ║
║   │             │                                        │    ║
║   │             │    [🔵 保存]   [⚪ 取消]              │    ║
║   └────────────┴────────────────────────────────────────┘    ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

#### 2.2.3 侧边栏 Tab 行为

- 左侧固定宽度：约 `140px`
- 7 个 Tab 项（垂直排列）：
  1. 通用（默认选中，显示应用基本信息）
  2. 分类管理
  3. 浏览器管理
  4. 游戏目录
  5. 忽略名单
  6. 数据库管理
  7. 崩溃日志与反馈
- 选中项：`#1E90FF` 背景 + 左侧白色竖条指示灯
- 悬停项：`#1a2a40` 背景
- 每个 Tab 前可带一个简单图标（文字符号或 emoji）

#### 2.2.4 通用标签页（默认首页）

- 显示应用 Logo + 名称 `UsageTracker`
- 显示版本号（从 `src/version.py` 读取）
- 显示许可证信息（GPL-3.0）
- 基本设置卡片：语言选择、开机自启开关、自动报告开关
- 底部：保存 + 取消按钮（使用卡片内布局）

### 2.3 实现方案

**方案**：tkinter Canvas 自绘 + 自定义样式类（`ui/styled_widgets.py`）
- 用 `Canvas.create_polygon(smooth=True)` 绘制圆角矩形
- 窗口背景用 `Canvas` 绘制径向渐变（渐变函数 `_draw_gradient`）
- 侧边栏用 `tk.Listbox` 或 Canvas 手绘（带发光指示器）
- 卡片用 `StyledFrame`（圆角 + 深色背景）
- 按钮用 `StyledButton`（自绘，带悬停/按下状态）
- 零额外依赖，保持项目精简原则
- 降级友好：渲染异常时自动回退到精简模式

**渐变背景实现要点**：
```python
def _draw_gradient(canvas, width, height, color1, color2):
    """在 Canvas 上绘制从上到下的渐变背景"""
    for i in range(height):
        ratio = i / height
        r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
        g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
        b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
        color = f'#{r:02x}{g:02x}{b:02x}'
        canvas.create_line(0, i, width, i, fill=color)
```

### 2.4 界面模式切换

- 配置项：`config.json → ui_mode: "simple" | "rich"`
- 默认值：安装后首次启动为 `rich`（精美模式）；后续保留上次选择
- 切换方式：设置窗口右上角按钮（双向切换）
- 切换后重启设置窗口生效，不需要重启整个程序

### 2.5 安装引导首次界面

安装完成后首次打开 UsageTracker：
1. 启动精美模式设置界面
2. 显示欢迎卡片：Logo + 应用简介
3. 引导用户完成初始设置（开机自启、通知开关、语言）
4. 用户点击"开始追踪" → 关闭引导，程序进入正常追踪模式

**触发条件**：`config.json → first_run: true`（安装时写入，完成引导后设为 `false`）

**涉及文件**：`ui/styled_widgets.py`（新建）、`ui/onboarding.py`（新建引导逻辑）、`ui/settings_window.py`（模式切换）、`src/config_manager.py`（新增 `ui_mode`、`first_run`）、`src/main.py`（首次启动检测）、`installer.iss`（安装后写入 `first_run=true`）

---

## 三、事件驱动追踪（替代 5 秒轮询）

### 3.1 背景

**现状**：v0.1.x 使用 5 秒轮询检测前台窗口，存在两个问题：
- 短窗口切换（< 5s）可能丢失
- 定时唤醒带来不必要的 CPU 开销

**v0.2.0 方案**：
- 引入 Windows `SetWinEventHook` 监听 `EVENT_SYSTEM_FOREGROUND`
- 零延迟检测窗口切换，仅在切换事件时触发记录
- 保留轮询作为降级方案（UWP 应用事件不稳定时自动回退）
- 新增设置项："检测模式"（自动 / 轮询 / 事件驱动）

**收益**：
- 短窗口切换不再丢失
- CPU 开销从定时唤醒降为纯事件驱动
- 电池续航提升（尤其笔记本）

### 3.2 实现要点

```python
# src/tracker.py — 事件驱动核心
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

# 事件回调
WinEventProc = ctypes.WINFUNCTYPE(None, wintypes.HANDLE, wintypes.DWORD,
                                   wintypes.HWND, wintypes.LONG,
                                   wintypes.LONG, wintypes.DWORD, wintypes.DWORD)

def on_foreground_changed(hWinEventHook, event, hwnd, idObject,
                          idChild, dwEventThread, dwmsEventTime):
    """前台窗口切换时触发"""
    tracker.on_window_changed(hwnd)

# 注册事件钩子
hook = user32.SetWinEventHook(
    0x0003,  # EVENT_SYSTEM_FOREGROUND
    0x0003,  # EVENT_SYSTEM_FOREGROUND
    0, WinEventProc(on_foreground_changed), 0, 0, 0x0002  # WINEVENT_OUTOFCONTEXT
)
```

**降级策略**：
- 首次运行尝试事件驱动模式
- 连续 3 次事件丢失（超时无回调）→ 自动降级为轮询模式
- 下次启动重新尝试事件驱动

**涉及文件**：`src/tracker.py`、`ui/tab_general.py`（新增检测模式选项）、`src/i18n.py`（新增翻译 key）

---

## 四、自动更新机制

### 4.1 方案设计

- 程序启动时检查 GitHub Releases API 的最新版本
- 比较本地版本号与远程版本号
- 有新版本时托盘弹出通知："新版本 vX.Y.Z 可用"
- 点击通知打开 GitHub Releases 页面手动下载
- 不做静默更新（避免权限问题）

### 4.2 版本检查逻辑

```python
# src/updater.py（新文件）
import urllib.request
import json

GITHUB_API = "https://api.github.com/repos/GiftedScout/UsageTracker/releases/latest"

def check_update(current_version: str) -> dict | None:
    """检查是否有新版本，返回版本信息或 None"""
    try:
        with urllib.request.urlopen(GITHUB_API, timeout=10) as resp:
            data = json.loads(resp.read())
        latest = data["tag_name"].lstrip("v")
        if latest > current_version:
            return {
                "version": latest,
                "url": data["html_url"],
                "notes": data.get("body", "")
            }
    except Exception:
        pass
    return None
```

### 4.3 配置项

| 配置 | 默认值 | 说明 |
|:---|:---|:---|
| `check_update` | `true` | 是否自动检查更新 |
| `check_update_freq` | `"startup"` | 检查频率：startup / daily / weekly |

### 4.4 UI 变更

- 设置界面"通用"标签页新增：更新检查开关 + 检查频率下拉框
- 新增"立即检查"按钮
- 托盘右键菜单新增"检查更新"

**涉及文件**：`src/updater.py`（新建）、`src/main.py`、`src/tray_app.py`、`ui/tab_general.py`、`src/config_manager.py`

---

## 五、报告增强

### 5.1 周报/月报趋势对比

- 月报增加**同比对比**（本月 vs 上月）
- 周报增加**周环比**（本周 vs 上周）
- 趋势箭头（↑↓→）和百分比变化

**实现**：`src/reporter.py` 查询相邻周期数据，计算差值和百分比

### 5.2 自定义报告时间范围

- 设置界面或托盘菜单新增"自定义报告"入口
- 用户选择任意起止日期，生成对应报告
- 复用现有日报模板，查询时替换日期范围

**涉及文件**：`src/reporter.py`、`src/tray_app.py`（菜单项）、`src/i18n.py`

### 5.3 报告导出 PDF

- 报告页面增加"导出 PDF"按钮
- 方案：调用系统自带的 Edge 无头模式打印 PDF（无需额外依赖）
- 备选方案：降级为提示用户手动 Ctrl+P 打印

```python
# 利用 Edge/Chromium 无头模式导出 PDF
import subprocess
def export_pdf(html_path: str, pdf_path: str):
    chrome_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    ]
    for chrome in chrome_paths:
        if Path(chrome).exists():
            subprocess.run([
                chrome, "--headless", "--disable-gpu",
                f"--print-to-pdf={pdf_path}", html_path
            ], check=True)
            return True
    return False
```

**涉及文件**：`src/reporter.py`（新增导出函数）、报告 HTML 模板（新增按钮）

### 5.4 报告内筛选/搜索

- 日报应用明细增加**分类筛选器**（下拉框选择分类）
- 支持按应用名搜索
- 时长排名支持升序/降序切换

**涉及文件**：`assets/themes/*.css`、报告 HTML 模板、`src/reporter.py`

---

## 六、分类系统增强

### 6.1 自动分类建议

- 追踪一段时间后，分析"其他"分类中使用频率高的应用
- 在设置界面"分类管理"标签页显示建议列表
- 用户一键接受或忽略

**实现**：
- `src/app_classifier.py` 新增 `get_suggestions()` 方法
- 统计"其他"分类中累计使用时间 Top 10 的应用
- `ui/tab_categories.py` 新增建议面板

### 6.2 浏览器子分类

- 通过窗口标题关键词推断浏览场景
- 例如：标签页含 "GitHub" "Stack Overflow" → 工作；含 "Bilibili" "YouTube" → 娱乐
- 用户可自定义关键词规则

**涉及文件**：`src/app_classifier.py`、`src/config_manager.py`（新增规则存储）

---

## 七、性能优化

### 7.1 数据库优化

- 大表增加复合索引（`app_name + date`）
- 写入策略：批量写入替代逐条写入（积累 N 条后 commit）
- WAL 模式提升并发读写

### 7.2 内存优化

- 追踪器 sessions 改为循环缓冲区（内存中只保留最近 N 条）
- 历史数据完全依赖数据库

### 7.3 启动优化

- 延迟加载非必要模块（设置界面、报告生成器首次使用时才 import）
- 游戏扫描异步执行，不阻塞启动

---

## 八、安装体验优化

### 8.1 静默安装

- 安装包支持 `/SILENT` 和 `/VERYSILENT` 参数
- 适合企业批量部署

### 8.2 便携版

- 提供免安装 ZIP 包
- 数据默认存放在 exe 同级目录
- 适合 U 盘携带使用

---

## 九、实施顺序

```
Phase 1: 视觉升级（快速完成）
  ├─ 提交 README 图标 + 封面 + QQ 群入口
  └─ 更新 README 路线图中的版本标记

Phase 2: 设置界面 UI 升级
  ├─ ui/styled_widgets.py — 封装自定义风格控件
  ├─ ui/settings_window.py — 精简/精美双模式切换
  ├─ ui/onboarding.py — 安装后首次引导界面
  ├─ src/config_manager.py — 新增 ui_mode / first_run
  └─ src/main.py — 首次运行检测 + 引导入口

Phase 3: 事件驱动追踪（核心改动）
  ├─ tracker.py 重构为事件驱动 + 轮询降级
  ├─ 设置界面新增检测模式选项
  └─ 充分测试 UWP 应用兼容性

Phase 4: 自动更新
  ├─ 新建 src/updater.py
  ├─ main.py 启动时检查更新
  ├─ 托盘菜单 + 设置界面集成
  └─ 测试版本比较逻辑

Phase 5: 报告增强
  ├─ 趋势对比（周环比 / 月同比）
  ├─ 自定义时间范围报告
  ├─ PDF 导出
  └─ 报告内筛选/搜索

Phase 6: 分类增强
  ├─ 自动分类建议
  └─ 浏览器子分类

Phase 7: 性能优化 + 安装体验
  ├─ 数据库索引 + WAL
  ├─ 内存/启动优化
  ├─ 静默安装支持
  └─ 便携版打包

Phase 8: 打包发版
  ├─ version.py 更新
  ├─ PyInstaller 打包
  ├─ Inno Setup 编译
  └─ GitHub Release 发布
```

---

## 十、不在 v0.2.0 范围内

以下功能推迟到后续版本：

| 功能 | 预估版本 | 推迟原因 |
|:---|:---|:---|
| 浏览器域名精准追踪（CDP） | v0.3.0 | 依赖 Edge 调试端口配置，用户门槛高；CLI 版已有参考实现 |
| 应用图标真实提取（exe） | v0.3.0 | PowerShell 提取方案需测试打包兼容性 |
| 数据库加密 | v0.3.0 | SQLCipher 增加依赖和复杂度 |
| 跨平台（macOS/Linux） | v1.0 | 架构改动大，需单独规划 |
| 云同步 | v1.0 | 需要后端服务支持 |
| 插件系统 | v1.2 | 需要稳定的 API 设计 |

---

## 十一、风险与注意事项

| 风险 | 应对措施 |
|:---|:---|
| 事件驱动在部分系统上不稳定 | 保留轮询降级方案，3 次失败自动切换 |
| GitHub API 限流（60次/小时） | 仅启动时检查一次，缓存结果到本地 |
| Edge 无头模式导出 PDF 不可用 | 降级为提示用户手动 Ctrl+P 打印 |
| i18n 新增 key 遗漏 | `t()` 函数 key 不存在时返回 key 本身，便于排查 |
| 精美模式自绘性能问题 | Canvas 重绘限频（50ms debounce），非关键路径延迟加载 |
| 首次引导与设置窗口状态冲突 | first_run 完成后才允许正常打开设置，引导期间禁用托盘设置入口 |

---

*本文档随开发进度持续更新。*
