<h1 align="center">🖥️ UsageTracker</h1>

<p align="right">
  中文 | <a href="README.md">English</a>
</p>

<p align="center">
  <b>Windows 桌面应用使用时长追踪工具</b><br>
  轻量静默驻守系统托盘，自动记录你的屏幕时间
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-v0.1.2-blue" alt="Version">
  <img src="https://img.shields.io/badge/platform-Windows_10%2F11-0078D6" alt="Platform">
  <img src="https://img.shields.io/badge/license-GPL--3.0-green" alt="License">
  <img src="https://img.shields.io/badge/lang-English%20%7C%20%E4%B8%AD%E6%96%87-orange" alt="Languages">
</p>

---

### 🎯 如何使用

#### 📥 直接使用（推荐）

**不想折腾代码？直接下载安装包即可：**

🔗 **[👉 前往 Releases 页面下载安装包](../../releases)**

1. 下载最新的 `UsageTracker_Setup_x.x.x.exe`
2. 双击运行安装向导（启动时可选择语言）
3. 安装完成后程序自动启动，最小化到右下角托盘

> 💡 日常使用无需任何操作，程序会在后台默默记录。右键托盘图标可以查看日报、打开设置等。

#### 📊 查看报告

- **今日日报**：右键托盘图标 → 点击「昨日日报」
- **周报 / 月报**：右键托盘图标 → 点击「上周周报」或「上月月报」
- 报告以精美 HTML 页面打开，包含交互图表、应用排行榜、游戏时长对比等
- 支持 🌸童话风 / 💼商务风 / 📝极简风 三套主题，在设置中切换

#### ⚙️ 常用设置

右键托盘图标 → 「设置」，可调整：

| 功能 | 说明 |
|:---|:---|
| **通用** | 报告主题（3 套风格）、数据保留策略、语言切换、开关开机自启、开机自动弹出昨日报告 |
| **忽略名单** | 添加不想被统计的程序，支持从当前运行进程中选择添加、移除选中、清空全部 |
| **分类管理** | 创建自定义分类（可选颜色），将程序通过文件选择器或运行进程列表归入分类 |
| **浏览器管理** | 查看已识别浏览器（内置 7 种），支持手动添加自定义浏览器 |
| **游戏管理** | 自动识别 Steam 游戏，支持手动添加或从运行进程中选择游戏 |
| **数据库管理** | 查看数据库大小，按保留策略清理过期数据，按日期范围导出 CSV |
| **运行日志** | 查看程序运行日志、导出反馈包用于 Bug 反馈 |

#### 🚫 在报告中忽略应用

打开日报后，应用明细表每行右侧有一个 **✕** 按钮，点击即可忽略该应用，下次报告将不再显示。

---

### 🌟 核心特色

- **🪟 自动追踪**：开机即运行，自动记录你使用了哪些应用、用了多久，无需手动操作
- **🌐 浏览器分类**：Chrome、Edge、Firefox 等浏览器分别统计，精准掌握上网时间
- **🎮 游戏识别**：自动识别 Steam 游戏、米哈游系列等，独立记录游戏时长
- **📊 可视化报告**：日报 / 周报 / 月报，带交互图表，三套主题随心切换
- **🔔 超时提醒**：浏览器或游戏使用过久时弹出系统通知，提醒你休息
- **🛡️ 纯本地运行**：不联网、不上传、无广告，所有数据仅存于你的电脑
- **🌐 中英双语**：完整支持中文和英文，安装时选择语言，也可在设置中随时切换

---

### ⬇️ 以下内容仅供开发者阅读

> ⚠️ **如果你只是想使用本软件，上方内容已经足够。以下为开发相关文档，非开发者无需继续阅读。**

---

### 🛠️ 关于本地开发

本项目采用 **Python 3.11+** 开发，依赖极简（仅 3 个），克隆后三步即可启动：

```bash
# 1. 克隆仓库
git clone https://github.com/GiftedScout/UsageTracker.git
cd UsageTracker

# 2. 创建虚拟环境并安装依赖
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 3. 启动
python -m src.main
```

> 启动后程序最小化到系统托盘（右下角），右键托盘图标可打开日报或设置面板。

---

### 📦 关于安装包构建

项目采用 **PyInstaller + Inno Setup** 双阶段打包：

```bash
# 安装打包依赖
pip install pyinstaller

# 第一阶段：PyInstaller → 单目录 exe
pyinstaller UsageTracker.spec

# 第二阶段：Inno Setup → 安装包（需安装 Inno Setup）
iscc installer.iss
```

---

### 📁 项目文件结构

| 文件 / 文件夹 | 说明 |
|:---|:---|
| `src/` | 核心业务模块（追踪引擎、数据存储、报告生成、通知系统、国际化等） |
| `ui/` | 图形设置界面（7 个功能标签页） |
| `locales/` | 翻译文件（zh-CN.json、en.json） |
| `assets/` | 静态资源（应用图标、Chart.js、报告主题 CSS） |
| `docs/` | 设计文档 |
| `installer.iss` | Inno Setup 安装脚本 |
| `requirements.txt` | Python 依赖清单 |
| `LICENSE` | GPL-3.0 开源许可证 |

---

### 🛠️ 技术栈

| 层级 | 技术选型 |
|:---|:---|
| 语言 | Python 3.11+ |
| GUI | tkinter + pystray + Pillow |
| 数据库 | SQLite（标准库） |
| 图表 | Chart.js（内嵌至报告） |
| 国际化 | 自研轻量 JSON 翻译模块 |
| 打包 | PyInstaller → Inno Setup |
| 依赖 | 仅 psutil + pystray + Pillow，极致轻量 |

---

### 🗺️ 版本路线图

- [x] **v0.1.0** — Bug 修复，中英双语支持
- [x] **v0.1.1** — 稳定性改进，崩溃修复
- [x] **v0.1.2** — 忽略名单修复，进程选择器，关于对话框
- [ ] **v0.2.0** — 事件驱动追踪（替代轮询）、自动更新机制、代码签名
- [ ] **v1.0.0** — 插件系统、跨平台适配（macOS / Linux）

---

### 🔗 相关链接

| 类型 | 链接 |
|:---|:---|
| GitHub 仓库 | https://github.com/GiftedScout/UsageTracker |
| 许可证 | [GPL-3.0](LICENSE) |
| 详细设计报告 | [docs/design-report-v0.1.0-beta.md](docs/design-report-v0.1.0-beta.md) |

---

<p align="center">
  <sub>Built with ❤️ by chaos · Licensed under GPL-3.0</sub>
</p>
