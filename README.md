<h1 align="center">🖥️ UsageTracker</h1>

<p align="center">
  <b>Windows 桌面应用使用时长追踪工具</b><br>
  静默驻守系统托盘，毫秒级感知你的每一次窗口切换
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-v0.1.0--beta-blue" alt="Version">
  <img src="https://img.shields.io/badge/platform-Windows_10%2F11-0078D6" alt="Platform">
  <img src="https://img.shields.io/badge/python-3.11%2B-3776AB" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
</p>

---

### 🌟 极致核心特色 (Core Features)

- **🪟 毫秒级窗口感知 (Window Tracking Engine)**：底层调用 Windows `GetForegroundWindow` / `IsIconic` API，每 5 秒精准轮询前台窗口，严格区分活跃焦点与最小化挂起状态，真正做到"你用什么，它就记什么"。
- **🌐 智能浏览器分账 (Browser Recognition)**：自动识别 Chrome、Edge、Firefox 等 7 种主流浏览器进程，每种浏览器独立统计时长，告别笼统的"浏览器"大类，精确掌控你的上网时间分布。
- **🎮 硬核游戏检测矩阵 (Game Detection)**：三重识别引擎并行运作——Steam 本地库扫描、米哈游注册表特征探测、已知游戏白名单兜底，无论是 3A 大作还是独立小品，统统无处遁形。
- **📊 三套美学报告引擎 (Visual Report Generator)**：日报 / 周报 / 月报全自动生成，内嵌 Chart.js 交互图表，提供 🌸童话风 / 💼商务风 / 📝极简风 三套精心打磨的 CSS 主题，数据可视化不再千篇一律。
- **🔔 智能超时熔断提醒 (Usage Alert System)**：浏览器与游戏使用时长触发阈值后，Windows 原生 Toast 通知即时弹出，温柔但坚定地提醒你"该休息了"。
- **🚀 报告内一键忽略 (In-Report Ignore)**：直接在 HTML 日报中点击应用旁的忽略按钮，通过本地 HTTP Bridge 链路即时生效，无需再打开设置面板手动配置。
- **🛡️ 零入侵隐私架构 (Privacy-First)**：所有数据严格存储于本地安装目录，不联网、不上传、无遥测、无广告、无第三方 SDK。开源代码，完全可审计。

---

### 🛠️ 关于本地部署 (Local Execution)

本项目秉持 **"大道至简"** 的架构理念，零配置起飞。克隆仓库后只需三步即可启动：

```bash
# 1. 克隆仓库
git clone https://github.com/GiftedScout/UsageTracker.git
cd UsageTracker

# 2. 创建虚拟环境并安装依赖
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 3. 启动追踪引擎
python -m src.main
```

> 💡 启动后程序自动最小化到系统托盘（右下角），右键托盘图标即可打开日报、切换报告主题或进入设置面板。

---

### 📦 关于安装包构建 (Build Installer)

项目采用 **PyInstaller + Inno Setup** 双阶段打包，输出标准 Windows 安装程序（含中文向导、开机自启、桌面快捷方式）：

```bash
# 安装打包依赖
pip install pyinstaller

# 第一阶段：PyInstaller → 单目录 exe
pyinstaller UsageTracker.spec

# 第二阶段：Inno Setup → 安装包（需安装 Inno Setup）
iscc installer.iss
```

> 安装包输出至 `installer_output/UsageTracker_Setup_0.1.0-beta.exe`（约 14.5 MB）

---

### 📁 项目文件结构 (Project Structure)

| 文件 / 文件夹 | 说明 |
|:---|:---|
| `src/` | 核心业务模块（追踪引擎、数据存储、报告生成、通知系统等） |
| `ui/` | tkinter 图形设置界面（7 个功能标签页） |
| `assets/` | 静态资源（应用图标、Chart.js、报告主题 CSS） |
| `docs/` | 设计文档（详细设计报告 + v0.2.0 路线图） |
| `installer.iss` | Inno Setup 安装脚本 |
| `requirements.txt` | Python 依赖清单 |
| `LICENSE` | MIT 开源许可证 |

---

### ⚙️ 核心配置说明 (Configuration)

配置文件位于安装目录下 `config/config.json`，也可通过图形设置面板实时修改：

| 配置项 | 默认值 | 说明 |
|:---|:---|:---|
| `poll_interval` | `5` | 窗口检测轮询间隔（秒） |
| `browser_limit` | `120` | 浏览器超时提醒阈值（分钟） |
| `game_limit` | `60` | 游戏超时提醒阈值（分钟） |
| `report_theme` | `fairy_tale` | 报告主题（fairy_tale / business / minimal） |
| `ignored_apps` | `[]` | 忽略的应用列表 |
| `notifications_enabled` | `true` | 是否启用超时通知 |

---

### 🛠️ 技术栈 (Tech Stack)

| 层级 | 技术选型 |
|:---|:---|
| 语言 | Python 3.11+ |
| GUI | tkinter + pystray + Pillow |
| 数据库 | SQLite（标准库） |
| 图表 | Chart.js（内嵌至报告） |
| 打包 | PyInstaller → Inno Setup |
| 进程通信 | HTTP Bridge (127.0.0.1:19234) |

---

### 🗺️ 版本路线图 (Roadmap)

详见 [docs/roadmap-v0.2.0.md](docs/roadmap-v0.2.0.md)

- [ ] **v0.2.0** — 事件驱动追踪（替代轮询）、自动更新机制、代码签名
- [ ] **v0.3.0** — 数据导出（CSV / PDF）、多语言支持、周报自动生成
- [ ] **v1.0.0** — 插件系统、跨平台适配（macOS / Linux）

---

### ✉️ 关于开发者 (About Developer)

**UsageTracker** 由 **chaos** 独立设计与开发，首发于 2026 年春季。

> 本项目完全出于个人需求驱动——我想知道自己每天的时间究竟去了哪里。

---

### 🔗 相关链接 (Links)

| 类型 | 链接 |
|:---|:---|
| GitHub 仓库 | https://github.com/GiftedScout/UsageTracker |
| 许可证 | [MIT](LICENSE) |
| v0.2.0 路线图 | [docs/roadmap-v0.2.0.md](docs/roadmap-v0.2.0.md) |
| 详细设计报告 | [docs/design-report-v0.1.0-beta.md](docs/design-report-v0.1.0-beta.md) |

---

<p align="center">
  <sub>Built with ❤️ by chaos · Licensed under MIT</sub>
</p>
