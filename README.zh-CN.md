<p align="center">
  <img src="assets/banner.png" alt="UsageTracker 封面" width="800">
</p>

<h1 align="center"><img src="assets/logo.png" width="48" alt="Logo"> UsageTracker</h1>

<p align="right">
  中文 | <a href="README.md">English</a>
</p>

<p align="center">
  <b>Linux-first 桌面使用时长追踪工具</b><br>
  轻量后台守护进程，静默记录你的屏幕时间
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-v0.4.0--linux--prerelease-blue" alt="Version">
  <img src="https://img.shields.io/badge/platform-Linux%20%28X11%2FXWayland%29-1793D1" alt="Platform">
  <img src="https://img.shields.io/badge/license-GPL--3.0-green" alt="License">
  <img src="https://img.shields.io/badge/lang-English%20%7C%20%E4%B8%AD%E6%96%87-orange" alt="Languages">
  <img src="https://img.shields.io/badge/headless-ready-brightgreen" alt="Headless Ready">
</p>

---

## 🎯 快速上手（源码运行）

> **Linux 优先，无 exe、无安装包，git clone 即可运行。**

```bash
# 1. 克隆仓库
git clone https://github.com/GiftedScout/UsageTracker.git
cd UsageTracker

# 2. 创建并激活虚拟环境
python3 -m venv venv
source venv/bin/activate

# 3. 安装依赖
#    最小安装（仅 daemon + WebUI）：pip install psutil
#    完整安装（含系统托盘）：       pip install -r requirements.txt
pip install psutil

# 4. 启动守护进程（无头模式，无托盘）
./bin/usagetracker daemon

# 5. 在浏览器中打开 WebUI 设置界面
#    → http://127.0.0.1:19234/settings
```

> **注意：** 程序以后台守护进程方式运行。关闭浏览器标签页不会退出程序。
> 停止方式：`./bin/usagetracker stop` 或 `python -m src.main stop`（需在仓库根目录执行）。

---

## 🖥️ CLI 接口

CLI 已可用。在仓库根目录可使用 `python -m src.main`；如果从任意工作目录调用，请使用绝对路径的 `bin/usagetracker` 包装器（例如 `/path/to/UsageTracker/bin/usagetracker status`）：

```bash
# 启动无头守护进程（无托盘）
./bin/usagetracker daemon

# 启动并显示系统托盘（需安装 pystray + Pillow）
./bin/usagetracker daemon --tray

# 在浏览器中打开 WebUI 设置
./bin/usagetracker web

# 查看今日使用概况
./bin/usagetracker today

# 检查守护进程状态
./bin/usagetracker status

# 优雅停止守护进程
./bin/usagetracker stop

# 查看帮助
./bin/usagetracker --help
```

详细 Linux Phase 1 计划见 [docs/roadmap-v0.3.0.md](docs/roadmap-v0.3.0.md)。

---

## 🌐 WebUI 设置（主要配置入口）

设置界面在本地 Web 服务器上运行，地址 **`http://127.0.0.1:19234/settings`**。

在任意浏览器中打开即可配置所有追踪选项：

| 功能 | 说明 |
|:-----|:-----|
| **通用** | 语言切换、开关开机自启、开机自动弹出昨日报告 |
| **应用分类** | 查看/编辑自定义分类，通过运行进程列表归入分类 |
| **浏览器管理** | 查看已识别浏览器（内置 7 种），支持手动添加自定义浏览器 |
| **项目目录** | 配置常用开发/工作项目目录，用于后续 Linux-first 项目上下文分析 |
| **忽略名单** | 添加不想被统计的程序，支持从当前运行进程中选择添加、移除、清空全部 |
| **数据库管理** | 查看数据库大小与记录数、预览最近数据、清理旧数据、备份数据库 |
| **反馈与日志** | 调整日志等级（DEBUG/INFO/WARNING/ERROR）、查看运行日志、提交反馈 |

> 设置页面支持中英文双语，提供 🌸童话风 / 💼极客风 双主题。

---

## 🔔 通知

- **Ubuntu/Linux 桌面：** 使用 `notify-send` 发送使用时长提醒（例如"你已使用 Firefox 1 小时"）。
- **降级策略：** 若 `notify-send` 不可用，通知静默退化为日志输出（不会崩溃）。

---

## 🔲 可选：系统托盘图标

系统托盘图标是**可选的**，不会阻断守护进程运行：

- **安装托盘依赖：** `pip install pystray Pillow`
- **需要 Linux 系统托盘支持：** 托盘图标需要托盘宿主（GNOME Extension `appindicator`、`trayer`、`tint2` 等）
- **无托盘模式：** 守护进程仍正常追踪、提供 WebUI 服务、发送通知
- **启用托盘启动：** `python -m src.main`（当前）或 `usage-tracker daemon --tray`（规划中）

如果 `pystray` 未安装，守护进程会打印日志信息并继续运行。

---

## ❌ 非目标（Phase 1）

| 项目 | 状态 |
|:-----|:-----|
| ❌ Windows exe / Inno Setup 安装包 | **不计划** — Linux 源码分发 |
| ❌ 对齐 Windows 源码 | **不计划** — linux-port 分支独立发展 |
| ❌ 游戏优先分类 | **不计划** — Linux 默认分类：开发、终端、浏览器、通信等 |
| ❌ 原生 GNOME Wayland 窗口检测 | **Phase 2+** — Phase 1 仅支持 XWayland，原生 Wayland 降级不崩溃 |
| ❌ Wayland AppIndicator 托盘 | **Phase 2+** — Phase 1 仅 X11/XWayland 托盘，非阻断 |
| ❌ systemd user service 自动安装 | **未来规划** — Phase 1 使用 XDG autostart |

---

## 📁 项目文件结构

```
UsageTracker/
├── src/                      # 核心 Python 模块
│   ├── main.py               # 主入口：追踪器 → Bridge → （可选）托盘
│   ├── tracker.py            # 前台窗口追踪器（Linux: xprop 轮询）
│   ├── app_classifier.py     # 应用分类器（Linux-first 默认分类）
│   ├── bridge_handler.py     # HTTP 服务 (127.0.0.1:19234) + WebUI + REST API
│   ├── notifier.py           # 使用时长通知（Linux: notify-send）
│   ├── platform_utils.py     # 跨平台抽象层（Linux: xprop, fcntl, XDG）
│   ├── data_store.py         # SQLite 数据层（零平台耦合）
│   ├── reporter.py           # 日报/周报/月报 HTML 生成
│   ├── config_manager.py     # JSON 配置管理
│   ├── singleton.py          # 单实例保护（Linux: fcntl 文件锁）
│   ├── startup_manager.py    # 开机自启（Linux: XDG autostart .desktop）
│   ├── tray_app.py           # pystray 系统托盘（可选，懒加载）
│   ├── constants.py          # 全局常量与 XDG 路径
│   ├── crash_handler.py      # 异常崩溃处理
│   ├── onboarding_web.py     # 首次运行引导页
│   ├── updater.py            # 更新检查
│   ├── i18n.py               # 国际化（zh-CN / en）
│   └── version.py            # v0.4.0-linux-prerelease
├── ui/web/                   # WebUI（HTML/CSS/JS）
│   ├── index.html            # 设置页面（双语）
│   ├── js/app.js             # 前端逻辑（REST API 客户端）
│   └── css/                  # 双主题（fairy-tale.css, geek.css）
├── assets/                   # 静态资源（图标、Chart.js、报告主题）
├── docs/                     # 设计文档与路线图
├── bin/                      # Linux 入口脚本（规划中）
├── requirements.txt          # Python 依赖（核心 + 可选）
└── LICENSE                   # GPL-3.0 开源许可证
```

---

## 🛠️ 技术栈

| 层级 | 技术选型 |
|:-----|:---------|
| 语言 | Python 3.11+ |
| 界面 | Web UI（HTML/CSS/JS）+ 可选 pystray（系统托盘） |
| 数据库 | SQLite（标准库） |
| 图表 | Chart.js（内嵌至报告） |
| 国际化 | 自研轻量 JSON 翻译模块 |
| 系统工具 | `xprop`（前台窗口检测）、`notify-send`（桌面通知） |
| 核心依赖 | `psutil` — 系统进程信息 |
| 可选依赖 | `pystray` + `Pillow` — 系统托盘图标 |
| 分发方式 | **git clone + venv**（无 exe、无安装包） |

---

## 🗺️ 版本路线图

- [x] **v0.1.0–v0.3.0** — Windows 原始版本：Bug 修复、中英双语、WebUI 迁移
- [x] **v0.4.0-linux-prerelease** — Linux 移植：跨平台抽象、XDG 路径、notify-send、X11 追踪
- [ ] **Phase 1a** — CLI daemon 入口、WebUI 优先、托盘可选、pidfile 停止
- [ ] **Phase 1b** — Linux 通知完善、XDG 自启、浏览器检测
- [ ] **Phase 1c** — 可选 AppIndicator 托盘（GNOME Wayland）
- [ ] **Phase 2+** — 原生 Wayland 窗口检测、systemd 服务、插件系统

---

## 🔗 相关链接

| 类型 | 链接 |
|:-----|:-----|
| GitHub 仓库 | https://github.com/GiftedScout/UsageTracker |
| 许可证 | [GPL-3.0](LICENSE) |
| 详细设计报告 | [docs/design-report-v0.1.0-beta.md](docs/design-report-v0.1.0-beta.md) |
| Linux 移植计划 | [docs/roadmap-v0.3.0.md](docs/roadmap-v0.3.0.md) |

---

<p align="center">
  <sub>Built with ❤️ by chaos · Licensed under GPL-3.0 · Linux-first 版本</sub>
</p>
