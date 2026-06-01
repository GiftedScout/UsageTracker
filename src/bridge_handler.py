"""
报告 ↔ 主进程通信 + 网页端设置服务
- 轻量 HTTP 服务（127.0.0.1:19234）
- 接收来自 HTML 报告的 ignore 请求
- 提供网页端设置界面（/settings）和 REST API
- 兼容文件轮询 bridge 目录（旧方案）
"""

import json
import logging
import mimetypes
import os
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

logger = logging.getLogger(__name__)

VALID_ACTIONS = {'ignore_app'}
_BRIDGE_PORT = 19234
_MAX_BODY = 2 * 1024 * 1024  # 2MB


class BridgeHandler:
    """报告与主进程的桥接通信 + 网页端设置服务"""

    def __init__(self, bridge_dir: str | None = None, poll_interval: int = 30):
        if bridge_dir is None:
            from .constants import BRIDGE_DIR
            self.bridge_dir = BRIDGE_DIR
        else:
            self.bridge_dir = Path(bridge_dir)
        self.bridge_dir.mkdir(parents=True, exist_ok=True)
        self.poll_interval = poll_interval
        self._stop_event = None
        self._http_server = None
        self._config_manager = None
        self._data_store = None
        self._exe_path = ''

    # ── ignore 处理（复用） ──────────────────────────────

    def _handle_ignore(self, exe_path: str, app_name: str) -> bool:
        if not exe_path and app_name:
            exe_path = self._resolve_exe_by_name(app_name)
        if not exe_path:
            logger.warning('忽略操作缺少 exe_path 且无法匹配: %s', app_name)
            return False
        if self._config_manager:
            self._config_manager.add_ignored_app(exe_path, app_name)
        if self._data_store:
            self._data_store.add_ignored_app(exe_path, app_name)
        logger.info('已忽略应用: %s (%s)', app_name, exe_path)
        return True

    @staticmethod
    def _resolve_exe_by_name(app_name: str) -> str:
        import psutil
        name_lower = app_name.lower()
        try:
            for p in psutil.process_iter(['name', 'exe']):
                try:
                    if p.info['name'] and p.info['name'].lower() == name_lower:
                        return p.info['exe'] or ''
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass
        return ''

    # ── 文件轮询（旧方案，保留） ───────────────────

    def poll_once(self, config_manager=None, data_store=None) -> int:
        request_file = self.bridge_dir / 'ignore_request.json'
        if not request_file.exists():
            return 0
        try:
            with open(request_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            action = data.get('action', '')
            if action not in VALID_ACTIONS:
                logger.warning('未知的 bridge action: %s', action)
                request_file.unlink()
                return 0
            exe_path = data.get('exe_path', '')
            app_name = data.get('app_name', '')
            if not exe_path or not app_name:
                logger.warning('bridge 请求缺少必要字段')
                request_file.unlink()
                return 0
            if action == 'ignore_app':
                if self._handle_ignore(exe_path, app_name):
                    processed = 1
            request_file.unlink()
        except Exception as e:
            logger.error('处理 bridge 请求失败: %s', e)
            return 0
        return processed

    def start_polling(self, config_manager=None, data_store=None) -> 'threading.Thread':
        import threading
        self._stop_event = threading.Event()
        self._config_manager = config_manager
        self._data_store = data_store

        def _poll_loop():
            import time
            while not self._stop_event.is_set():
                try:
                    self.poll_once(config_manager, data_store)
                except Exception as e:
                    logger.error('bridge 轮询错误: %s', e)
                self._stop_event.wait(self.poll_interval)

        thread = threading.Thread(target=_poll_loop, daemon=True, name='bridge-poll')
        thread.start()
        logger.info('Bridge 轮询已启动（间隔 %d 秒）', self.poll_interval)
        return thread

    # ── HTTP 服务（扩展：设置页面 + API） ─────────

    def start_http_server(self, config_manager=None, data_store=None, exe_path: str = ''):
        import threading
        self._config_manager = config_manager
        self._data_store = data_store
        self._exe_path = exe_path
        bridge = self
        bridge._http_alive = threading.Event()
        bridge._http_alive.set()  # assume alive until proven otherwise

        class _Handler(BaseHTTPRequestHandler):
            # ── 路由分发 ──
            def do_GET(self):
                try:
                    self._do_GET_impl()
                except ConnectionResetError:
                    pass
                except BrokenPipeError:
                    pass
                except Exception as e:
                    logger.error('GET %s 未处理异常: %s', self.path, e)

            def _do_GET_impl(self):
                p = urllib.parse.urlparse(self.path)
                path = p.path
                qs = urllib.parse.parse_qs(p.query)

                # 引导页面
                if path == '/onboarding':
                    return self._serve_onboarding()

                # 设置页面
                if path == '/settings':
                    return self._serve_settings()

                # 静态文件
                if path.startswith('/static/'):
                    return self._serve_static(path)

                # API: 获取配置
                if path == '/api/config':
                    return self._api_get_config()

                # API: 获取应用分类列表
                if path == '/api/apps':
                    return self._api_get_apps()

                # API: 忽略名单
                if path == '/api/ignore':
                    return self._api_get_ignore()

                # API: 游戏目录
                if path == '/api/games':
                    return self._api_get_games()

                # API: 浏览器规则
                if path == '/api/browsers':
                    return self._api_get_browsers()

                # API: 数据库状态
                if path == '/api/database':
                    return self._api_get_database()

                # API: 崩溃日志
                if path == '/api/feedback/logs':
                    return self._api_get_feedback_logs()

                # API: 读取日志内容
                if path == '/api/feedback/logs/read':
                    return self._api_read_log()

                # API: 检查更新
                if path == '/api/check-update':
                    return self._api_check_update()

                # API: 健康检查
                if path == '/api/health':
                    return self._respond(200, {
                        'ok': True,
                        'timestamp': __import__('datetime').datetime.now().isoformat(),
                    })

                # API: 运行中进程列表（供进程选择器使用）
                if path == '/api/processes':
                    return self._api_get_processes()

                self._respond(404, {'ok': False, 'msg': 'Not found'})

            def do_POST(self):
                try:
                    self._do_POST_impl()
                except ConnectionResetError:
                    pass
                except BrokenPipeError:
                    pass
                except Exception as e:
                    logger.error('POST %s 未处理异常: %s', self.path, e)
                    try:
                        self._respond(500, {'ok': False, 'msg': str(e)})
                    except Exception:
                        pass

            def _do_POST_impl(self):
                p = urllib.parse.urlparse(self.path)
                path = p.path

                if path == '/api/config':
                    return self._api_post_config()

                if path == '/api/ignore':
                    return self._api_post_ignore()

                if path == '/api/apps':
                    return self._api_post_apps()

                if path == '/api/games':
                    return self._api_post_games()

                if path == '/api/browsers':
                    return self._api_post_browsers()

                if path == '/api/database':
                    return self._api_post_database()

                if path == '/api/export-pdf':
                    return self._api_post_export_pdf()

                if path == '/api/feedback':
                    return self._api_post_feedback()

                self._respond(404, {'ok': False, 'msg': 'Not found'})

            def do_OPTIONS(self):
                self.send_response(204)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.end_headers()

            # ── 响应工具 ──
            def _respond(self, code, data: dict, content_type='application/json; charset=utf-8'):
                body = json.dumps(data, ensure_ascii=False).encode('utf-8')
                self.send_response(code)
                self.send_header('Content-Type', content_type)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _respond_html(self, html: str):
                body = html.encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _read_body(self) -> dict:
                length = int(self.headers.get('Content-Length', 0))
                if length <= 0 or length > _MAX_BODY:
                    return {}
                return json.loads(self.rfile.read(length))

            # ── 静态文件服务 ──
            def _serve_static(self, path: str):
                from .constants import WEB_DIR
                # 安全：只允许 [a-zA-Z0-9_./-]，禁止 ..
                rel = path[len('/static/'):]
                if '..' in rel or rel.startswith('/'):
                    self._respond(400, {'ok': False, 'msg': 'Bad path'})
                    return
                file_path = WEB_DIR / rel
                if not file_path.exists() or not file_path.is_file():
                    self._respond(404, {'ok': False, 'msg': 'File not found'})
                    return
                mime, _ = mimetypes.guess_type(str(file_path))
                if not mime:
                    mime = 'application/octet-stream'
                try:
                    data = file_path.read_bytes()
                    self.send_response(200)
                    self.send_header('Content-Type', mime)
                    self.send_header('Content-Length', str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                except Exception as e:
                    logger.error('静态文件服务失败: %s', e)
                    self._respond(500, {'ok': False, 'msg': str(e)})

            # ── 引导页面 ──
            def _serve_onboarding(self):
                from .onboarding_web import render_onboarding_page
                theme = 'fairy'
                if bridge._config_manager:
                    theme = bridge._config_manager.get('web_theme', 'fairy')
                html = render_onboarding_page(theme)
                self._respond_html(html)

            # ── 设置页面 ──
            def _serve_settings(self):
                from .constants import WEB_DIR
                html_path = WEB_DIR / 'index.html'
                if html_path.exists():
                    return self._respond_html(html_path.read_text(encoding='utf-8'))
                # 兜底：返回简易提示页
                self._respond_html('''
                    <!doctype html><html><head><meta charset="utf-8">
                    <title>UsageTracker Settings</title></head>
                    <body style="background:#0a0f1a;color:#fff;font-family:sans-serif;
                                 display:flex;align-items:center;justify-content:center;height:100vh;">
                    <div style="text-align:center;">
                        <h1>UsageTracker</h1>
                        <p>网页端设置界面正在建设中，请稍后...</p>
                        <p style="color:#b0b8c8;font-size:14px;">需要先将 ui/web/ 目录部署到程序中。</p>
                    </div></body></html>
                ''')

            # ── API 实现 ──
            def _api_get_config(self):
                try:
                    cfg = bridge._config_manager
                    if not cfg:
                        self._respond(503, {'ok': False, 'msg': '服务未就绪'})
                        return
                    data = {
                        'ok': True,
                        'language': cfg.language,
                        'auto_start': cfg.auto_start,
                        'auto_show_daily_report': cfg.auto_show_daily_report,
                        'detection_mode': cfg.detection_mode,
                        'check_update': cfg.check_update,
                        'check_update_freq': cfg.check_update_freq,
                        'theme': cfg.get('theme', 'fairy_tale'),
                        'web_theme': cfg.get('web_theme', 'fairy'),
                        'version': cfg.get('version', ''),
                        'first_run': cfg.get('first_run', True),
                        'privacy_accepted': cfg.get('privacy_accepted', False),
                    }
                    self._respond(200, data)
                except Exception as e:
                    logger.error('API /config GET 失败: %s', e)
                    self._respond(500, {'ok': False, 'msg': str(e)})

            def _api_post_config(self):
                try:
                    body = self._read_body()
                    cfg = bridge._config_manager
                    if not cfg:
                        self._respond(503, {'ok': False, 'msg': '服务未就绪'})
                        return
                    # 只更新允许的字段
                    allowed = {
                        'language', 'auto_start', 'auto_show_daily_report',
                        'detection_mode', 'check_update', 'check_update_freq',
                        'theme', 'web_theme',
                        'first_run', 'privacy_accepted',
                    }
                    side_effects = []
                    for key in allowed:
                        if key in body:
                            cfg.set(key, body[key])
                            # auto_start side effect: 立即启用/禁用开机启动
                            if key == 'auto_start' and bridge._exe_path:
                                from .startup_manager import StartupManager
                                sm = StartupManager(exe_path=bridge._exe_path)
                                if body[key]:
                                    ok = sm.enable_startup()
                                    side_effects.append(f'开机启动{"已启用" if ok else "启用失败"}')
                                else:
                                    ok = sm.disable_startup()
                                    side_effects.append(f'开机启动{"已禁用" if ok else "禁用失败"}')
                    cfg.save()
                    msg = '配置已保存'
                    if side_effects:
                        msg += ' (' + '; '.join(side_effects) + ')'
                    self._respond(200, {'ok': True, 'msg': msg})
                except Exception as e:
                    logger.error('API /config POST 失败: %s', e)
                    self._respond(500, {'ok': False, 'msg': str(e)})

            def _api_get_apps(self):
                try:
                    cfg = bridge._config_manager
                    data = {
                        'ok': True,
                        'custom_categories': cfg.custom_categories if cfg else [],
                    }
                    self._respond(200, data)
                except Exception as e:
                    self._respond(500, {'ok': False, 'msg': str(e)})

            def _api_post_apps(self):
                try:
                    body = self._read_body()
                    cfg = bridge._config_manager
                    action = body.get('action', '')
                    if action == 'add_category':
                        cid = body.get('id', '')
                        name = body.get('name', '')
                        color = body.get('color', '#0078D4')
                        if cfg and cid and name:
                            ok = cfg.add_custom_category(cid, name, color)
                            if ok:
                                self._respond(200, {'ok': True, 'msg': '分类已添加'})
                            else:
                                self._respond(200, {'ok': False, 'msg': '分类 ID 或名称已存在'})
                        else:
                            self._respond(400, {'ok': False, 'msg': '参数不完整'})
                    elif action == 'remove_category':
                        cid = body.get('id', '')
                        if cfg and cid:
                            ok = cfg.remove_custom_category(cid)
                            self._respond(200, {'ok': ok, 'msg': '分类已删除' if ok else '分类不存在'})
                        else:
                            self._respond(400, {'ok': False, 'msg': '缺少 id'})
                    elif action == 'add_app':
                        cid = body.get('id', '')
                        exe = body.get('exe_path', '')
                        if cfg and cid and exe:
                            ok = cfg.add_app_to_category(cid, exe)
                            self._respond(200, {'ok': ok, 'msg': '应用已添加' if ok else '应用已在分类中'})
                        else:
                            self._respond(400, {'ok': False, 'msg': '参数不完整'})
                    elif action == 'remove_app':
                        cid = body.get('id', '')
                        exe = body.get('exe_path', '')
                        if cfg and cid and exe:
                            ok = cfg.remove_app_from_category(cid, exe)
                            self._respond(200, {'ok': ok, 'msg': '应用已移除' if ok else '应用不在分类中'})
                        else:
                            self._respond(400, {'ok': False, 'msg': '参数不完整'})
                    else:
                        self._respond(400, {'ok': False, 'msg': '未知 action'})
                except Exception as e:
                    self._respond(500, {'ok': False, 'msg': str(e)})

            def _api_get_ignore(self):
                try:
                    cfg = bridge._config_manager
                    self._respond(200, {
                        'ok': True,
                        'ignored_apps': cfg.ignored_apps if cfg else [],
                    })
                except Exception as e:
                    self._respond(500, {'ok': False, 'msg': str(e)})

            def _api_post_ignore(self):
                try:
                    body = self._read_body()
                    action = body.get('action', '')
                    cfg = bridge._config_manager
                    if action == 'add':
                        exe = body.get('exe_path', '')
                        name = body.get('app_name', '')
                        if cfg and exe:
                            cfg.add_ignored_app(exe, name or '')
                            self._respond(200, {'ok': True})
                        else:
                            self._respond(400, {'ok': False, 'msg': '缺少 exe_path'})
                    elif action == 'remove':
                        exe = body.get('exe_path', '')
                        if cfg and exe:
                            cfg.remove_ignored_app(exe)
                            self._respond(200, {'ok': True})
                        else:
                            self._respond(400, {'ok': False, 'msg': '缺少 exe_path'})
                    else:
                        self._respond(400, {'ok': False, 'msg': '未知 action'})
                except Exception as e:
                    self._respond(500, {'ok': False, 'msg': str(e)})

            def _api_get_games(self):
                try:
                    cfg = bridge._config_manager
                    self._respond(200, {
                        'ok': True,
                        'game_dirs': cfg.game_dirs if cfg else [],
                    })
                except Exception as e:
                    self._respond(500, {'ok': False, 'msg': str(e)})

            def _api_post_games(self):
                try:
                    body = self._read_body()
                    action = body.get('action', '')
                    cfg = bridge._config_manager
                    if action == 'add_dir':
                        d = body.get('dir', '')
                        if cfg and d and d not in cfg.game_dirs:
                            cfg.game_dirs.append(d)
                            cfg.save()
                            self._respond(200, {'ok': True})
                        else:
                            self._respond(400, {'ok': False, 'msg': '参数错误'})
                    elif action == 'remove_dir':
                        d = body.get('dir', '')
                        if cfg:
                            cfg.game_dirs = [x for x in cfg.game_dirs if x != d]
                            cfg.save()
                            self._respond(200, {'ok': True})
                    else:
                        self._respond(400, {'ok': False, 'msg': '未知 action'})
                except Exception as e:
                    self._respond(500, {'ok': False, 'msg': str(e)})

            def _api_get_browsers(self):
                try:
                    cfg = bridge._config_manager
                    self._respond(200, {
                        'ok': True,
                        'browsers': cfg.browsers if cfg else [],
                    })
                except Exception as e:
                    self._respond(500, {'ok': False, 'msg': str(e)})

            def _api_post_browsers(self):
                try:
                    body = self._read_body()
                    action = body.get('action', '')
                    cfg = bridge._config_manager
                    if action == 'add_rule':
                        rule = body.get('rule', {})
                        if cfg and rule:
                            cfg.browsers.append(rule)
                            cfg.save()
                            self._respond(200, {'ok': True})
                    elif action == 'remove_rule':
                        idx = body.get('index', -1)
                        if cfg and 0 <= idx < len(cfg.browsers):
                            cfg.browsers.pop(idx)
                            cfg.save()
                            self._respond(200, {'ok': True})
                    else:
                        self._respond(400, {'ok': False, 'msg': '未知 action'})
                except Exception as e:
                    self._respond(500, {'ok': False, 'msg': str(e)})

            def _api_get_database(self):
                try:
                    from .constants import DB_PATH, DATA_DIR
                    import os
                    db_file = DB_PATH
                    size = db_file.stat().st_size if db_file.exists() else 0
                    # 获取记录数
                    count = 0
                    if bridge._data_store:
                        try:
                            import sqlite3
                            conn = sqlite3.connect(str(db_file))
                            cur = conn.cursor()
                            cur.execute('SELECT COUNT(*) FROM usage_records')
                            count = cur.fetchone()[0]
                            conn.close()
                        except Exception:
                            pass
                    self._respond(200, {
                        'ok': True,
                        'db_size': size,
                        'db_size_mb': round(size / 1024 / 1024, 2),
                        'record_count': count,
                    })
                except Exception as e:
                    self._respond(500, {'ok': False, 'msg': str(e)})

            def _api_post_database(self):
                try:
                    body = self._read_body()
                    action = body.get('action', '')
                    if action == 'cleanup':
                        days = body.get('days', 90)
                        if bridge._data_store:
                            bridge._data_store.cleanup_old_data(days)
                            self._respond(200, {'ok': True, 'msg': f'已清理 {days} 天前的数据'})
                        else:
                            self._respond(503, {'ok': False, 'msg': '服务未就绪'})
                    elif action == 'backup':
                        import shutil
                        from .constants import DB_PATH, DATA_DIR
                        backup_path = DB_PATH.with_suffix('.backup.db')
                        if DB_PATH.exists():
                            shutil.copy2(DB_PATH, backup_path)
                            self._respond(200, {'ok': True, 'backup_path': str(backup_path)})
                        else:
                            self._respond(400, {'ok': False, 'msg': '数据库文件不存在'})
                    else:
                        self._respond(400, {'ok': False, 'msg': '未知 action'})
                except Exception as e:
                    self._respond(500, {'ok': False, 'msg': str(e)})

            def _api_get_feedback_logs(self):
                try:
                    from .constants import LOG_DIR, CRASH_LOG_DIR
                    logs = []
                    for log_dir in [LOG_DIR, CRASH_LOG_DIR]:
                        if log_dir.exists():
                            for f in sorted(log_dir.glob('*.log'), reverse=True)[:20]:
                                logs.append({'name': f.name, 'size': f.stat().st_size,
                                             'dir': str(log_dir.parent)})
                    self._respond(200, {'ok': True, 'logs': logs})
                except Exception as e:
                    self._respond(500, {'ok': False, 'msg': str(e)})

            def _api_read_log(self):
                """读取指定日志文件内容（最近 500 行）"""
                try:
                    from .constants import LOG_DIR, CRASH_LOG_DIR
                    # 从 self.path 解析 query string
                    _p = urllib.parse.urlparse(self.path)
                    qs = urllib.parse.parse_qs(_p.query)
                    fname = qs.get('file', [''])[0]
                    if not fname or '..' in fname or '/' in fname or '\\' in fname:
                        self._respond(400, {'ok': False, 'msg': '非法文件名'})
                        return
                    for log_dir in [LOG_DIR, CRASH_LOG_DIR]:
                        fpath = log_dir / fname
                        if fpath.exists() and fpath.is_file():
                            lines = fpath.read_text(encoding='utf-8',
                                                    errors='replace').splitlines()
                            # 返回最后 500 行
                            tail = lines[-500:]
                            content = '\n'.join(tail)
                            self._respond(200, {
                                'ok': True,
                                'file': fname,
                                'total_lines': len(lines),
                                'content': content,
                            })
                            return
                    self._respond(404, {'ok': False, 'msg': '文件不存在'})
                except Exception as e:
                    self._respond(500, {'ok': False, 'msg': str(e)})

            def _api_post_export_pdf(self):
                try:
                    length = int(self.headers.get('Content-Length', 0))
                    body = json.loads(self.rfile.read(length))
                    html_path = body.get('html_path', '')
                    if not html_path:
                        self._respond(400, {'ok': False, 'msg': '缺少 html_path'})
                        return
                    from .reporter import HTMLReportGenerator
                    pdf = HTMLReportGenerator.export_pdf(html_path)
                    if pdf:
                        self._respond(200, {'ok': True, 'pdf': pdf})
                    else:
                        self._respond(500, {'ok': False,
                            'msg': '导出 PDF 失败，请手动 Ctrl+P 打印为 PDF'})
                except Exception as e:
                    logger.error('PDF 导出请求失败: %s', e)
                    self._respond(500, {'ok': False, 'msg': str(e)})

            def _api_post_feedback(self):
                try:
                    body = self._read_body()
                    desc = body.get('description', '')
                    contact = body.get('contact', '')
                    if not desc:
                        self._respond(400, {'ok': False, 'msg': '描述不能为空'})
                        return
                    from .constants import FEEDBACK_DIR
                    FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
                    import datetime
                    fname = FEEDBACK_DIR / f'feedback_{datetime.datetime.now():%Y%m%d_%H%M%S}.json'
                    with open(fname, 'w', encoding='utf-8') as f:
                        json.dump({
                            'description': desc,
                            'contact': contact,
                            'time': datetime.datetime.now().isoformat(),
                        }, f, ensure_ascii=False, indent=2)
                    self._respond(200, {'ok': True, 'msg': '反馈已提交'})
                except Exception as e:
                    self._respond(500, {'ok': False, 'msg': str(e)})

            def _api_check_update(self):
                try:
                    from .version import VERSION
                    from .updater import check_update
                    info = check_update(VERSION)
                    if info:
                        self._respond(200, {'ok': True, 'update': info})
                    else:
                        self._respond(200, {'ok': True, 'update': None})
                except Exception as e:
                    self._respond(500, {'ok': False, 'msg': str(e)})

            def _api_get_processes(self):
                """返回当前运行中的进程列表，供网页端进程选择器使用"""
                try:
                    import psutil
                    seen = set()
                    processes = []
                    for p in psutil.process_iter(['name', 'exe', 'pid']):
                        try:
                            name = p.info.get('name', '')
                            exe = p.info.get('exe', '')
                            if not name or name.lower() in ('idle', 'system',
                                                             'registry'):
                                continue
                            # 按进程名去重（同名只保留一个）
                            key = name.lower()
                            if key in seen:
                                continue
                            seen.add(key)
                            processes.append({
                                'name': name,
                                'exe_path': exe or name,
                                'pid': p.info['pid'],
                            })
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                    processes.sort(key=lambda x: x['name'].lower())
                    self._respond(200, {
                        'ok': True,
                        'processes': processes[:300],
                    })
                except Exception as e:
                    logger.error('API /processes 失败: %s', e)
                    self._respond(500, {'ok': False, 'msg': str(e)})

            # ── 日志 ──
            def log_message(self, fmt, *args):
                logger.debug('bridge-http: ' + fmt, *args)

        try:
            self._http_server = ThreadingHTTPServer(('127.0.0.1', _BRIDGE_PORT), _Handler)
            self._http_server.daemon_threads = True
            logger.info('Bridge HTTP 服务已启动 (127.0.0.1:%d)', _BRIDGE_PORT)
        except OSError as e:
            logger.warning('Bridge HTTP 启动失败（端口被占用，跳过）: %s', e)
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0,
                f'UsageTracker HTTP 服务启动失败，端口 {_BRIDGE_PORT} 可能被占用。\n\n'
                f'请先关闭其他 UsageTracker 实例后重试。\n错误: {e}',
                'UsageTracker - 启动失败',
                0x40
            )
            return

        # HTTP 线程：带自动重启的 serve_forever
        def _http_loop():
            while True:
                if bridge._stop_event and bridge._stop_event.is_set():
                    break
                try:
                    bridge._http_alive.set()
                    self._http_server.serve_forever()
                except Exception as e:
                    logger.error('HTTP serve_forever 异常: %s', e, exc_info=True)
                bridge._http_alive.clear()
                if bridge._stop_event and bridge._stop_event.is_set():
                    break
                # 等待并重启
                import time
                logger.warning('HTTP 服务停止，5 秒后重启...')
                time.sleep(5)
                try:
                    self._http_server = ThreadingHTTPServer(
                        ('127.0.0.1', _BRIDGE_PORT), _Handler)
                    self._http_server.daemon_threads = True
                    logger.info('HTTP 服务已重启')
                except OSError as e2:
                    logger.error('HTTP 重启失败（端口冲突），30 秒后重试: %s', e2)
                    time.sleep(30)

        _thr = threading.Thread(target=_http_loop, daemon=True, name='bridge-http')
        _thr.start()

        # 心跳日志（每 5 分钟检查一次 HTTP 存活状态）
        def _heartbeat():
            import time
            while True:
                if bridge._stop_event and bridge._stop_event.is_set():
                    break
                time.sleep(300)
                if not bridge._http_alive.is_set():
                    logger.warning('HTTP 服务已停止响应！')
                else:
                    logger.debug('HTTP 心跳正常')

        _hb = threading.Thread(target=_heartbeat, daemon=True, name='bridge-hb')
        _hb.start()

    def stop_polling(self) -> None:
        if self._stop_event:
            self._stop_event.set()
        if self._http_server:
            try:
                self._http_server.shutdown()
            except Exception:
                pass
