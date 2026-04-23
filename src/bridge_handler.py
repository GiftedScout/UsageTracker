"""
报告 ↔ 主进程通信
- 轻量 HTTP 服务（127.0.0.1:19234），接收来自 HTML 报告的 ignore 请求
- 兼容文件轮询 bridge 目录（旧方案）
- 支持忽略应用操作
"""

import json
import logging
import os
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

logger = logging.getLogger(__name__)

VALID_ACTIONS = {'ignore_app'}
_BRIDGE_PORT = 19234


class BridgeHandler:
    """报告与主进程的桥接通信"""

    def __init__(self, bridge_dir: str | None = None, poll_interval: int = 30):
        if bridge_dir is None:
            from .constants import BRIDGE_DIR
            self.bridge_dir = BRIDGE_DIR
        else:
            self.bridge_dir = Path(bridge_dir)
        self.bridge_dir.mkdir(parents=True, exist_ok=True)
        self.poll_interval = poll_interval
        self._stop_event: 'threading.Event | None' = None
        self._http_server = None
        self._config_manager = None
        self._data_store = None

    def _handle_ignore(self, exe_path: str, app_name: str) -> bool:
        """执行忽略应用操作"""
        exe_path = os.path.realpath(exe_path)
        if self._config_manager:
            self._config_manager.add_ignored_app(exe_path, app_name)
        if self._data_store:
            self._data_store.add_ignored_app(exe_path, app_name)
        logger.info('已忽略应用: %s (%s)', app_name, exe_path)
        return True

    def poll_once(self, config_manager=None, data_store=None) -> int:
        """执行一次轮询，返回处理的请求数"""
        processed = 0
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
        return processed

    def start_polling(self, config_manager=None, data_store=None) -> 'threading.Thread':
        """启动后台轮询线程"""
        import threading
        self._stop_event = threading.Event()

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

    def start_http_server(self, config_manager=None, data_store=None):
        """启动轻量 HTTP 服务，供 HTML 报告发送 ignore 请求"""
        self._config_manager = config_manager
        self._data_store = data_store
        bridge = self

        class _Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                if self.path != '/ignore':
                    self.send_error(404)
                    return
                try:
                    length = int(self.headers.get('Content-Length', 0))
                    body = json.loads(self.rfile.read(length))
                    exe_path = body.get('exe_path', '')
                    app_name = body.get('app_name', '')
                    if not exe_path or not app_name:
                        self._respond(400, {'ok': False, 'msg': '缺少参数'})
                        return
                    bridge._handle_ignore(exe_path, app_name)
                    self._respond(200, {'ok': True, 'msg': f'已忽略: {app_name}'})
                except Exception as e:
                    logger.error('HTTP ignore 请求失败: %s', e)
                    self._respond(500, {'ok': False, 'msg': str(e)})

            def do_OPTIONS(self):
                self.send_response(204)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.end_headers()

            def _respond(self, code, data):
                self.send_response(code)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

            def log_message(self, fmt, *args):
                logger.debug('bridge-http: ' + fmt, *args)

        try:
            self._http_server = HTTPServer(('127.0.0.1', _BRIDGE_PORT), _Handler)
            import threading
            _thr = threading.Thread(target=self._http_server.serve_forever, daemon=True, name='bridge-http')
            _thr.start()
            logger.info('Bridge HTTP 服务已启动 (127.0.0.1:%d)', _BRIDGE_PORT)
        except OSError as e:
            logger.warning('Bridge HTTP 启动失败（端口被占用，跳过）: %s', e)

    def stop_polling(self) -> None:
        if self._stop_event:
            self._stop_event.set()
        if self._http_server:
            self._http_server.shutdown()
