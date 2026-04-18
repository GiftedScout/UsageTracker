# UsageTracker

> Windows 桌面应用使用时长追踪工具 —— 静默运行在系统托盘，自动记录你的屏幕时间。

<p align="center">
  <img src="assets/icon.ico" width="80" alt="UsageTracker Icon">
</p>

**版本**: v0.1.0 · **平台**: Windows 10/11 · **许可证**: MIT

---

## ✨ 功能亮点

| 功能 | 说明 |
|------|------|
| 🖥️ **自动追踪** | 每 5 秒检测前台窗口，区分活跃/最小化，精确到秒 |
| 🌐 **浏览器识别** | 自动识别 Chrome/Edge/Firefox 等 7 种浏览器，分别统计 |
| 🎮 **游戏检测** | Steam 库扫描 + 米哈游注册表探测 + 白名单匹配 |
| 📊 **可视化报告** | 日报/周报/月报，内置 3 套主题 + Chart.js 图表 |
| 🔔 **超时提醒** | 浏览器/游戏使用超时 Toast 通知 |
| ⚙️ **图形设置** | tkinter 设置面板，支持忽略名单、分类管理、日志查看 |
| 🚀 **一键忽略** | 在 HTML 报告中直接点击忽略按钮，无需打开设置 |
| 💾 **开机自启** | 安装时可选开启，静默启动不弹窗 |

## 📁 项目结构

```
UsageTracker/
├── src/                      # 核心模块
│   ├── main.py               # 入口：初始化 → 启动追踪 → 系统托盘
│   ├── tracker.py            # 窗口追踪引擎（Win32 API）
│   ├── data_store.py         # SQLite 数据存储 + 日聚合
│   ├── app_classifier.py     # 应用分类（浏览器/游戏/系统）
│   ├── config_manager.py     # 配置管理（JSON）
│   ├── reporter.py           # HTML 报告生成器（日报/周报/月报）
│   ├── notifier.py           # Windows Toast 通知
│   ├── bridge_handler.py     # 报告↔主进程 HTTP 通信
│   ├── startup_manager.py    # 开机自启管理
│   ├── crash_handler.py      # 崩溃捕获与日志
│   ├── constants.py          # 全局常量 + 路径 + 旧数据迁移
│   ├── singleton.py          # 单例模式
│   └── version.py            # 版本号
├── ui/                       # 设置界面（tkinter）
│   ├── settings_window.py    # 设置主窗口
│   ├── tab_general.py        # 通用设置
│   ├── tab_browsers.py       # 浏览器管理
│   ├── tab_games.py          # 游戏管理
│   ├── tab_categories.py     # 分类规则
│   ├── tab_ignore.py         # 忽略名单
│   ├── tab_database.py       # 数据库管理
│   └── tab_feedback.py       # 运行日志 + 反馈导出
├── assets/
│   ├── icon.ico              # 应用图标
│   ├── chart.umd.min.js      # Chart.js（内嵌到报告）
│   └── themes/               # 报告主题
│       ├── fairy_tale.css    # 🌸 童话风（默认）
│       ├── business.css      # 💼 商务风
│       └── minimal.css       # 📝 极简风
├── installer.iss             # Inno Setup 安装脚本
├── requirements.txt          # Python 依赖
└── docs/                     # 设计文档
    ├── design-report-v0.1.0-beta.md
    └── roadmap-v0.2.0.md
```

## 🚀 快速开始

### 从安装包安装（推荐）

1. 前往 [Releases](../../releases) 下载最新安装包
2. 运行 `UsageTracker_Setup_0.1.0-beta.exe`
3. 安装向导中勾选「开机自动启动」
4. 安装完成后程序自动运行，最小化到系统托盘

### 从源码运行（开发者）

**环境要求**：
- Python 3.11+
- Windows 10/11

```bash
# 克隆仓库
git clone https://github.com/chaos/UsageTracker.git
cd UsageTracker

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动
python -m src.main
```

> 启动后程序最小化到系统托盘（右下角），右键托盘图标可打开日报或设置。

### 打包安装包

```bash
# 安装打包工具
pip install pyinstaller

# 打包为 exe（单目录模式）
pyinstaller UsageTracker.spec

# 用 Inno Setup 生成安装包
iscc installer.iss
```

安装包输出到 `installer_output/UsageTracker_Setup_0.1.0-beta.exe`

## 📊 报告预览

UsageTracker 生成精美的 HTML 报告，支持 3 种主题风格：

- 🌸 **童话风** — 柔和渐变 + 圆角卡片，默认主题
- 💼 **商务风** — 深色调 + 清晰对比
- 📝 **极简风** — 留白充足，数据优先

报告包含：使用时长饼图、分类柱状图、应用排行榜、游戏时长对比等。

## 🔧 配置说明

配置文件位于安装目录下 `config/config.json`，也可通过设置界面修改：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `poll_interval` | 5 | 追踪轮询间隔（秒） |
| `browser_limit` | 120 | 浏览器超时提醒（分钟） |
| `game_limit` | 60 | 游戏超时提醒（分钟） |
| `report_theme` | fairy_tale | 报告主题 |
| `ignored_apps` | [] | 忽略的应用列表 |
| `notifications_enabled` | true | 是否启用超时通知 |

## 🗂️ 数据存储

所有数据存储在**安装目录**下，卸载时默认保留：

```
{安装目录}/
├── data/
│   └── usage_data.db      # SQLite 数据库
├── config/
│   └── config.json         # 用户配置
├── reports/                 # HTML 报告
├── logs/                    # 运行日志
├── bridge/                  # 报告通信临时文件
└── feedback/                # 反馈导出包
```

## 🛡️ 隐私声明

- **所有数据仅存储在本地**，不联网、不上传
- 无遥测、无广告、无第三方 SDK
- 开源代码，可自行审计

## 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| 语言 | Python 3.11+ |
| GUI | tkinter（系统托盘：pystray + Pillow） |
| 数据库 | SQLite（标准库） |
| 图表 | Chart.js（CDN 内嵌） |
| 打包 | PyInstaller → Inno Setup |
| 进程通信 | HTTP (127.0.0.1:19234) |

## 📋 依赖

```
psutil>=5.9.0      # 进程信息
pystray>=0.19.0    # 系统托盘
Pillow>=10.0.0     # 图标渲染
```

## 🗺️ 路线图

详见 [docs/roadmap-v0.2.0.md](docs/roadmap-v0.2.0.md)

- [ ] **v0.2.0** — 事件驱动追踪、自动更新、代码签名
- [ ] **v0.3.0** — 数据导出（CSV/PDF）、多语言、周报自动邮件
- [ ] **v1.0.0** — 插件系统、跨平台（macOS/Linux）

## 📄 许可证

[MIT](LICENSE) © 2026 chaos
