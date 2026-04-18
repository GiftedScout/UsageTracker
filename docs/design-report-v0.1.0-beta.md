# UsageTracker v0.1.0-beta 详细设计报告

> **文档版本**: 1.0  
> **创建日期**: 2026-04-16  
> **项目状态**: 设计阶段（待实施）  
> **源码参考**: `C:\Users\chaos\WorkBuddy\20260330195834\usage_tracker\`

---

## 一、项目背景

### 1.1 现有成果

UsageTracker 是一个 Windows 前台应用使用时长追踪工具，当前为 Python 命令行程序，已实现核心功能：

- **窗口追踪**：通过 Windows API (`GetForegroundWindow` / `IsIconic`) 每 5 秒检测前台窗口，区分活跃/最小化状态
- **应用分类**：自动识别浏览器（7种）、游戏（Steam 库扫描 + 米哈游注册表探测 + 已知白名单兜底）、系统进程黑名单过滤
- **数据存储**：SQLite 单表 `usage_records`，按日聚合，参数化查询
- **HTML 报告**：日报/周报/月报，内置原神童话风 CSS + Chart.js 图表
- **通知提醒**：浏览器/游戏使用超时 Toast 通知
- **开机启动**：启动文件夹快捷方式 + 注册表双方案
- **自动保存**：每 5 分钟增量写入数据库，防止进程中断丢数据

### 1.2 标准化目标

将 CLI 工具重构为可分发的 Windows 桌面应用（exe 安装包），供无 Python 环境的普通用户使用。

---

## 二、功能规格

### 2.1 系统托盘

| 功能 | 说明 |
|------|------|
| **右键菜单** | 今日日报、上周周报、上月月报、设置、关于、退出 |
| **双击行为** | 打开今日日报 |
| **Tooltip** | 悬浮显示 "UsageTracker \| 今日：浏览器 2h30m / 游戏 1h15m" |
| **实时更新** | Tooltip 每 30 秒刷新当日累计数据 |

### 2.2 安装引导（Inno Setup）

| 步骤 | 内容 |
|------|------|
| 欢迎页 | 应用名称、版本号 |
| 隐私声明 | "所有数据仅存储在本地，不联网不上传" |
| 目录选择 | 默认 `%LOCALAPPDATA%\Programs\UsageTracker` |
| 开机自启 | 默认勾选，附说明文案：*"UsageTracker 需要在开机时自动启动才能记录您的使用数据。如不开启，每次需要手动运行程序。"* |
| 桌面快捷方式 | 可选创建 |
| 安装/卸载 | 进度条，完成后可立即启动 |
| 卸载选项 | 默认保留数据，提供勾选"同时删除使用数据" |

### 2.3 图形设置界面（tkinter）

7 个标签页：

| 标签页 | 功能 |
|--------|------|
| 通用设置 | 主题选择（简约/童话/商务）、数据保留策略（无限制/1年/3个月/1个月）、开机自启开关、隐私声明、版本信息 |
| 分类管理 | 预设分类（浏览器/游戏/其他）+ 用户自定义分类（工作/学习等），每个分类可指定应用归属和颜色 |
| 浏览器管理 | 动态识别已安装浏览器 + 手动添加/移除 |
| 游戏目录 | 自动扫描 Steam/Epic 游戏 + 手动添加目录，虚假 exe 过滤，游戏列表展示 |
| 忽略名单 | 从 HTML 报告右键/设置界面添加忽略，显示应用名/exe路径/忽略时间 |
| 数据库管理 | 数据库大小、数据清理（按保留策略）、CSV 导出 |
| 崩溃日志与反馈 | 崩溃日志列表/查看详情、问题反馈表单（描述+邮箱）、生成反馈包 |

窗口规格：约 700×500，居中显示，底部 确定/取消/应用 按钮。

### 2.4 多主题报告

| 主题 | 风格 |
|------|------|
| 简约（Minimal） | 扁平化设计，中性色系，简洁线条 |
| 童话（Fairy Tale） | 现有原神风格，金色+粉色+薄荷绿，圆角卡片，装饰星星 |
| 商务（Business） | 深蓝+灰色，数据仪表盘风格，锐利边框 |

报告 HTML 中注入对应主题 CSS 文件，Chart.js 图表颜色跟随主题配色。

### 2.5 忽略名单

- **触发方式**：HTML 报告中应用条目右键 → "忽略此应用的统计"
- **通信机制**：报告 JS 写入 `%LOCALAPPDATA%\UsageTracker\bridge\ignore_request.json`，主进程每 30 秒轮询处理
- **存储**：以 `exe_path` 为唯一标识（非进程名），存入 config.json + 数据库
- **管理**：设置界面"忽略名单"标签页可查看/移除

### 2.6 崩溃自恢复

- **检测**：主进程异常退出（非 exit code 0）
- **恢复**：外层 crash_handler 通知用户（PowerShell Toast）后自动重启
- **限制**：最多重试 3 次，超限后放弃并提示
- **日志**：崩溃 traceback 写入 `%LOCALAPPDATA%\UsageTracker\crash_logs\crash_YYYYMMDD_HHMMSS.log`

### 2.7 单实例保障

- Windows 命名 Mutex（`Global\UsageTracker_SingleInstance`）
- 启动时检测，已有实例运行则通知并退出

### 2.8 数据管理

| 功能 | 说明 |
|------|------|
| 隐私声明 | 首次启动弹窗，用户确认后不再显示 |
| 数据导出 | CSV 格式，按日期范围可选 |
| 数据保留 | 无限制 / 1年 / 3个月 / 1个月，过期自动清理 |
| 配置持久化 | `%APPDATA%\UsageTracker\config.json`，卸载不丢失 |
| 版本信息 | v0.1.0-beta，托盘"关于"显示，Semantic Versioning |

---

## 三、技术架构

### 3.1 技术栈

| 组件 | 选型 | 理由 |
|------|------|------|
| 语言 | Python 3.10+ | 现有代码基础 |
| GUI 框架 | tkinter | 内置，零依赖，体积小 |
| 系统托盘 | pystray + Pillow | Python 标准托盘库 |
| 通知 | PowerShell Toast | 现有方案，去掉 plyer |
| 数据存储 | SQLite | 现有方案，轻量无服务 |
| 报告渲染 | HTML + Chart.js | 现有方案，CDN 加载 |
| 打包 | PyInstaller (--onedir) | 主流，成熟 |
| 安装器 | Inno Setup 6 | 脚本友好，体验好 |
| 版本管理 | Semantic Versioning | 行业标准 |

### 3.2 依赖清单

```
psutil>=5.9.0    # 进程信息获取
pystray>=0.19.0  # 系统托盘图标/菜单
Pillow>=10.0.0   # 图像处理（pystray 依赖）
```

**移除**：`plyer>=2.1.0`（已有 PowerShell Toast，冗余备选）

### 3.3 架构图

```
┌──────────────────────────────────────────────────────────┐
│                     UsageTracker.exe                       │
│                                                            │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │  System Tray │  │  Tray Menu   │  │  Settings UI    │  │
│  │  (pystray)   │──│  Handler     │  │  (tkinter)      │  │
│  └──────┬───────┘  └──────────────┘  └────────┬────────┘  │
│         │                                    │            │
│  ┌──────▼────────────────────────────────────▼─────────┐  │
│  │              App Controller (main.py)                │  │
│  │   单实例锁 │ 崩溃恢复 │ 首次启动 │ 托盘初始化        │  │
│  └──┬─────────┬──────────┬──────────┬──────────┬──────┘  │
│     │         │          │          │          │         │
│  ┌──▼───┐ ┌──▼────┐ ┌───▼───┐ ┌───▼────┐ ┌──▼──────┐  │
│  │Track │ │Data   │ │Report │ │Config  │ │Bridge   │  │
│  │Core  │ │Store  │ │Gen    │ │Manager │ │Handler  │  │
│  └──┬───┘ └──┬────┘ └───┬───┘ └───┬────┘ └─────────┘  │
│     │        │          │         │                      │
│  ┌──▼────────▼──────────▼─────────▼──────────────────┐  │
│  │           App Classifier (配置驱动)                 │  │
│  │   浏览器列表 / 游戏目录 / 忽略名单 / 自定义分类     │  │
│  └───────────────────────────────────────────────────┘  │
│                                                           │
│  ┌───────────────────────────────────────────────────┐   │
│  │                   Data Layer                      │   │
│  │  %LOCALAPPDATA%\UsageTracker\                     │   │
│  │    usage_data.db  │  config.json                  │   │
│  │    reports\       │  logs\                        │   │
│  │    crash_logs\    │  bridge\                      │   │
│  │    steam_games.json                               │   │
│  └───────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

### 3.4 目录结构

```
UsageTracker/
├── src/
│   ├── main.py                    # GUI 应用入口
│   ├── tray_app.py                # 系统托盘核心
│   ├── tracker.py                 # 窗口追踪（从原项目适配）
│   ├── app_classifier.py          # 配置驱动的分类器
│   ├── notifier.py                # Toast 通知（去掉 plyer）
│   ├── data_store.py              # 数据存储（扩展表+CSV导出+清理）
│   ├── reporter.py                # 报告生成（多主题系统）
│   ├── startup_manager.py         # 开机启动管理
│   ├── config_manager.py          # 配置读写/默认值/迁移
│   ├── singleton.py               # 单实例 Mutex
│   ├── crash_handler.py           # 崩溃恢复包装器
│   ├── bridge_handler.py          # 报告↔主进程通信
│   ├── version.py                 # 版本号 v0.1.0-beta
│   └── constants.py               # 全局常量
├── ui/
│   ├── settings_window.py         # 设置主窗口
│   ├── tab_general.py             # 通用设置
│   ├── tab_categories.py          # 分类管理
│   ├── tab_browsers.py            # 浏览器管理
│   ├── tab_games.py               # 游戏目录
│   ├── tab_ignore.py              # 忽略名单
│   ├── tab_database.py            # 数据库管理
│   └── tab_feedback.py            # 崩溃日志与反馈
├── assets/
│   ├── icon.ico                   # 托盘图标（16/32/48）
│   └── themes/
│       ├── minimal.css            # 简约风格
│       ├── fairy_tale.css         # 童话风格（从 reporter.py 提取）
│       └── business.css           # 商务风格
├── installer/
│   ├── UsageTracker.iss           # Inno Setup 脚本
│   └── setup_banner.bmp           # 安装向导横幅（可选）
├── build/
│   ├── UsageTracker.spec          # PyInstaller 配置
│   └── build.bat                  # 一键构建
├── requirements.txt
└── README.md
```

---

## 四、关键模块设计

### 4.1 config_manager.py — 配置管理

```python
# config.json 默认结构
DEFAULT_CONFIG = {
    "version": "0.1.0-beta",
    "theme": "fairy_tale",           # minimal | fairy_tale | business
    "data_retention": "unlimited",    # unlimited | 1year | 3months | 1month
    "check_interval": 5,             # 追踪检测间隔（秒）
    "auto_start": True,
    "privacy_accepted": False,
    "browsers": [...],               # 用户自定义浏览器列表
    "game_dirs": [...],              # 用户添加的游戏目录
    "ignored_apps": [                # 忽略名单
        {"exe_path": "...", "app_name": "...", "ignored_at": "..."}
    ],
    "custom_categories": [           # 用户自定义分类
        {"id": "...", "name": "工作", "color": "#0078D4", "apps": ["code.exe"]}
    ]
}
```

- 存储路径：`%APPDATA%\UsageTracker\config.json`
- 写入策略：先写临时文件 → `os.replace` 原子替换
- 读取策略：schema 校验，非法值回退默认值
- 迁移策略：版本号比对，逐版本迁移函数

### 4.2 app_classifier.py — 配置驱动的分类器

**重构要点**：

| 原实现 | 新实现 |
|--------|--------|
| `BROWSERS` 硬编码集合 | 从 config.json 读取 + 自动检测补充 |
| `GAME_LAUNCHERS` 硬编码 | 保留硬编码（不可修改） |
| `SYSTEM_PROCESS_BLACKLIST` 硬编码 | 保留硬编码（不可修改） |
| `HELPER_EXE_BLACKLIST` 硬编码 | 保留硬编码（不可修改） |
| `KNOWN_GAMES` 硬编码白名单 | 保留硬编码（兜底用） |
| `should_skip()` 仅检查进程名 | 同时检查 exe_path 是否在忽略名单中 |
| `classify()` 仅返回 browser/game/other | 支持自定义分类 |
| Steam 游戏扫描结果存 steam_games.json | 同步写入 config.json |

**分类优先级**：

1. 系统黑名单 → skip（不记录）
2. 忽略名单（exe_path） → skip（不记录）
3. 用户自定义分类规则（exe_path 匹配） → 用户分类
4. 浏览器列表匹配 → browser
5. 游戏平台启动器 → other
6. Steam/非 Steam 游戏匹配 → game
7. 兜底 → other

### 4.3 data_store.py — 数据库扩展

**新增表**：

```sql
-- 忽略应用记录（冗余存储，便于查询和统计）
CREATE TABLE IF NOT EXISTS ignored_apps (
    exe_path TEXT PRIMARY KEY,
    app_name TEXT NOT NULL,
    ignored_at TEXT NOT NULL
);

-- 自定义分类规则
CREATE TABLE IF NOT EXISTS custom_categories (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    color TEXT DEFAULT '#0078D4',
    created_at TEXT NOT NULL
);

-- 应用→分类映射
CREATE TABLE IF NOT EXISTS app_category_rules (
    exe_path TEXT NOT NULL,
    category_id TEXT NOT NULL,
    FOREIGN KEY (category_id) REFERENCES custom_categories(id),
    PRIMARY KEY (exe_path, category_id)
);

-- 数据库 schema 版本
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);
```

**新增方法**：

- `export_to_csv(output_path, start_date, end_date)` — CSV 导出
- `cleanup_expired_data(retention_policy)` — 按策略清理
- `get_database_size()` — 返回数据库文件大小
- `add_ignored_app(exe_path, app_name)` — 添加忽略
- `remove_ignored_app(exe_path)` — 移除忽略
- `get_all_ignored_apps()` — 获取所有忽略列表
- `add_custom_category(...)` / `remove_custom_category(...)` — 分类 CRUD
- `add_app_to_category(...)` / `remove_app_from_category(...)` — 分类规则 CRUD

**迁移策略**：

`_init_database` 中检查 `schema_version` 表，版本为空则从 0 开始逐版本迁移。

### 4.4 reporter.py — 多主题系统

**抽象方案**：

```python
class Theme:
    """主题配置"""
    name: str           # 主题 ID
    display_name: str   # 显示名
    css_file: str       # CSS 文件路径
    chart_colors: dict  # Chart.js 配色方案
    html_header: str    # HTML 头部装饰模板

THEMES = {
    'minimal': Theme('minimal', '简约', 'minimal.css', ...),
    'fairy_tale': Theme('fairy_tale', '童话', 'fairy_tale.css', ...),
    'business': Theme('business', '商务', 'business.css', ...),
}
```

- 从现有 `reporter.py` 的 `_GENSHIN_CSS` 提取为 `fairy_tale.css` 文件
- 日报/周报/月报生成方法接受 `theme` 参数
- HTML 报告注入对应主题 CSS 和 Chart.js 配色
- 报告中的每个应用条目添加 `data-exe-path` 属性（供忽略交互使用）

### 4.5 singleton.py — 单实例保障

```python
import ctypes

class SingleInstance:
    def __init__(self, mutex_name: str = "Global\\UsageTracker_SingleInstance"):
        self.mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
        self.already_running = ctypes.windll.kernel32.GetLastError() == 183  # ERROR_ALREADY_EXISTS
    
    def __del__(self):
        if self.mutex:
            ctypes.windll.kernel32.ReleaseMutex(self.mutex)
            ctypes.windll.kernel32.CloseHandle(self.mutex)
```

### 4.6 crash_handler.py — 崩溃恢复

```python
class CrashHandler:
    MAX_RETRIES = 3
    RETRY_COUNT_FILE = "%LOCALAPPDATA%/UsageTracker/crash_retry_count"
    
    def wrap(self, target_func):
        """包装主进程入口，异常退出时自动重启"""
        while True:
            try:
                sys.exit(target_func())
            except SystemExit:
                break
            except Exception:
                self._write_crash_log()
                retry_count = self._get_retry_count()
                if retry_count >= self.MAX_RETRIES:
                    self._notify_user_max_retries()
                    break
                self._increment_retry_count()
                self._notify_user_retrying(retry_count + 1)
        self._clear_retry_count()
```

### 4.7 bridge_handler.py — 报告↔主进程通信

```python
class BridgeHandler:
    BRIDGE_DIR = "%LOCALAPPDATA%/UsageTracker/bridge"
    POLL_INTERVAL = 30  # 秒
    
    def poll(self):
        """轮询 bridge 目录，处理请求"""
        # 检查 ignore_request.json
        # 校验 JSON schema（必须包含 exe_path, app_name, action）
        # 调用 config_manager / data_store 更新忽略名单
        # 删除已处理的请求文件
```

**安全设计**：
- 请求文件必须包含 `action` 字段，只处理已知 action（`ignore_app`）
- `exe_path` 必须是绝对路径且经过 `os.path.realpath` 规范化
- 处理完成后立即删除请求文件，防止重复处理

### 4.8 tray_app.py — 系统托盘

```python
class TrayApp:
    def __init__(self, icon_path, data_store, config_manager, ...):
        self.icon = pystray.Icon(
            name='UsageTracker',
            icon=Image.open(icon_path),
            title='UsageTracker',
            menu=pystray.Menu(
                pystray.MenuItem('今日日报', self.open_daily_report),
                pystray.MenuItem('上周周报', self.open_weekly_report),
                pystray.MenuItem('上月月报', self.open_monthly_report),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem('设置', self.open_settings),
                pystray.MenuItem('关于', self.show_about),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem('退出', self.quit, default=True),
            ),
            on_double_click=self.open_daily_report,
        )
    
    def update_tooltip(self):
        """更新悬浮提示：今日实时统计"""
        # 从 data_store 查询今日数据
        # 格式化："UsageTracker | 今日：浏览器 2h30m / 游戏 1h15m"
    
    def run(self):
        """启动托盘图标（阻塞）"""
        self.icon.run()
```

---

## 五、数据路径规划

| 数据类型 | 路径 | 说明 |
|----------|------|------|
| 数据库 | `%LOCALAPPDATA%\UsageTracker\usage_data.db` | SQLite |
| 配置文件 | `%APPDATA%\UsageTracker\config.json` | 用户偏好 |
| HTML 报告 | `%LOCALAPPDATA%\UsageTracker\reports\` | 日报/周报/月报 |
| 运行日志 | `%LOCALAPPDATA%\UsageTracker\logs\` | 按日期命名 |
| 崩溃日志 | `%LOCALAPPDATA%\UsageTracker\crash_logs\` | 带时间戳 |
| Bridge 通信 | `%LOCALAPPDATA%\UsageTracker\bridge\` | 临时请求文件 |
| Steam 缓存 | `%LOCALAPPDATA%\UsageTracker\steam_games.json` | 游戏列表缓存 |
| 反馈包 | `%LOCALAPPDATA%\UsageTracker\feedback\` | 导出的反馈文件 |
| 安装目录 | `%LOCALAPPDATA%\Programs\UsageTracker\` | exe + 资源文件 |

**隔离原则**：
- `%APPDATA%`（漫游）存配置（跨机器同步友好）
- `%LOCALAPPDATA%`（本地）存数据（体积大、不跨机器）

---

## 六、安装器设计（Inno Setup）

### 6.1 安装步骤

```
欢迎页 → 隐私声明页 → 目录选择（默认 %LOCALAPPDATA%\Programs\UsageTracker）
→ 开机自启（默认勾选+说明） → 桌面快捷方式（可选） → 安装进度 → 完成
```

### 6.2 卸载行为

- 默认**保留** `%LOCALAPPDATA%\UsageTracker\` 全部数据
- 提供**可选勾选**："同时删除使用数据（包括数据库、配置、报告等）"
- 删除注册表启动项（如有）
- 删除开始菜单/桌面快捷方式

### 6.3 安装后操作

- 注册表写入安装路径（`HKCU\Software\UsageTracker\InstallPath`）
- 创建 `unins000.exe`
- 若勾选开机自启：创建启动文件夹快捷方式

---

## 七、打包方案（PyInstaller）

### 7.1 打包配置

```
模式: --onedir（文件夹模式）
资源: assets/icon.ico, assets/themes/*.css
hiddenimports: psutil, pystray, PIL, ctypes.wintypes
UPX: 启用压缩
console: False（无控制台窗口）
```

### 7.2 构建流程

```
build.bat:
  1. python -m PyInstaller UsageTracker.spec
  2. ISCC installer/UsageTracker.iss
  3. 输出: installer/Output/UsageTracker_Setup.exe
```

---

## 八、工程质量规范

### 8.1 优先级

**安全性 > 简洁性 > 功能完备性**

### 8.2 安全性

| 风险 | 防护 |
|------|------|
| SQL 注入 | 全部参数化查询 |
| 文件误删 | 路径白名单，只操作 %LOCALAPPDATA%\UsageTracker\ 和安装目录 |
| 路径遍历 | `os.path.realpath` + 白名单校验 |
| 进程权限 | `psutil.AccessDenied` → graceful 降级 |
| 配置篡改 | schema 校验，非法值回退默认 |
| bridge 伪造 | JSON schema 校验，只处理已知 action |

### 8.3 简洁性

- 依赖最小化：仅 `psutil` + `pystray` + `Pillow`
- 函数 50 行以内，模块单一职责
- 轮询用 `Event.wait()`，数据库即用即关
- 每个 import 必须被引用，dead code 直接删除

### 8.4 完备性

- 每个 public 方法 try-except，graceful 降级
- 边界检查：日期、空数据、文件不存在、权限
- 状态一致性：DB 失败不影响内存；配置先写临时文件再 rename
- 日志分级：DEBUG/INFO/WARNING/ERROR
- 类型标注：Python 3.10+ 风格
- 文档字符串：每个 public 函数/类

### 8.5 编码规范

- 全中文注释（技术术语除外）
- 类型标注使用 `|` 替代 `Optional`/`Union`
- 错误处理不静默吞异常，至少 `logging.warning()`
- 配置变更原子写入（temp → os.replace）
- 数据库 schema 变更有版本号和迁移逻辑

---

## 九、实施计划

| 阶段 | 任务 | 依赖 |
|------|------|------|
| 1 | 项目骨架：目录结构、version.py、constants.py、config_manager.py、requirements.txt | 无 |
| 2 | 核心模块迁移：tracker.py、data_store.py（新表+CSV+清理）、notifier.py、app_classifier.py（配置驱动） | 阶段1 |
| 3 | 报告多主题：提取 CSS、新建简约/商务主题、HTML 注入 bridge 忽略交互 | 阶段1 |
| 4 | 基础设施：singleton.py、crash_handler.py | 阶段1 |
| 5 | 托盘应用：tray_app.py、startup_manager.py 适配、bridge_handler.py | 阶段2+3+4 |
| 6 | 设置 UI：settings_window.py + 7 个标签页 | 阶段2+3 |
| 7 | 主入口：main.py（隐私声明、托盘初始化、图标生成） | 阶段5+6 |
| 8 | 打包：PyInstaller spec + Inno Setup + build.bat | 阶段7 |

---

## 十、版本策略

- **当前版本**: v0.1.0-beta
- **版本格式**: MAJOR.MINOR.PATCH[-prerelease]
- **版本规则**:
  - MAJOR：不兼容的 API 变更
  - MINOR：向后兼容的功能新增
  - PATCH：向后兼容的缺陷修复
  - prerelease：alpha / beta / rc

---

## 附录 A：现有源码文件清单

| 文件 | 行数 | 功能 | 复用策略 |
|------|------|------|---------|
| tracker.py | 301 | 前台窗口追踪 | 直接复制，移除 CLI print |
| app_classifier.py | 494 | 应用分类 | 重构为配置驱动 |
| data_store.py | 504 | SQLite 存储 | 扩展新表和新方法 |
| reporter.py | 904 | HTML 报告 | 扩展多主题系统 |
| notifier.py | ~150 | Toast 通知 | 直接复制，移除 plyer |
| startup_manager.py | ~100 | 开机启动 | 适配 exe 路径 |
| main.py | 409 | CLI 入口 | 重写为 GUI 入口 |

## 附录 B：数据库 Schema v0→v1 迁移

```
v0 (现有):
  - usage_records (id, date, app_name, category, duration_seconds, session_count, created_at)
  - alert_records (id, date, category, alert_time, message)

v1 (新增):
  + schema_version (version)
  + ignored_apps (exe_path PK, app_name, ignored_at)
  + custom_categories (id PK, name UNIQUE, color, created_at)
  + app_category_rules (exe_path, category_id FK → custom_categories, PK=[exe_path, category_id])
  + usage_records 新增列: exe_path TEXT (可为 NULL，旧数据不填)
```
