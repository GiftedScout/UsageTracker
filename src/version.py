"""版本号"""

VERSION = "0.4.0"
APP_NAME = "UsageTracker"

RELEASE_NOTES = """\
版本 v0.4.0-prerelease

Linux 预发布版
• Linux-first 源码运行：新增 bin/usagetracker CLI 包装器，支持 daemon/status/stop/web/today
• XDG 路径适配：配置、数据、日志、报告迁移到 Linux 用户目录
• 活动窗口追踪：支持 X11/XWayland 环境，保留轮询模式避免事件钩子崩溃
• WebUI 与浏览器识别：兼容 Linux 进程信息结构，修复浏览器识别异常
• 忽略名单迁移：自动清理 Windows 默认 exe 残留，改用 Linux 默认忽略项
• 单实例与守护进程：锁文件不再被状态检查误清空，stop/status 可从 /proc/locks 兜底识别 PID
• 通知/启动项/报告：适配 notify-send、XDG autostart 与 Linux 文件打开方式

注意
• 这是 Linux 预发布版本，当前推荐在 X11/XWayland 会话下使用。
• 暂不提供 Windows 安装包；请通过 git clone + pip install 源码运行。
"""



