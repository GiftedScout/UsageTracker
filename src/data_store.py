"""
数据存储模块
- SQLite 持久化使用记录
- Schema 版本迁移（v0 → v1）
- CSV 导出、数据清理
"""

import csv
import logging
import os
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

CURRENT_SCHEMA_VERSION = 1


@dataclass
class DailyUsage:
    date: str
    app_name: str
    category: str
    duration_seconds: float
    session_count: int
    exe_path: str = ''


@dataclass
class DailyReport:
    date: str
    total_usage_seconds: float
    browser_seconds: float
    game_seconds: float
    other_seconds: float
    app_breakdown: dict[str, float]
    category_breakdown: dict[str, float]
    alerts_triggered: int


class DataStore:
    """数据存储管理器"""

    def __init__(self, db_path: str | None = None):
        if db_path is None:
            from .constants import DB_PATH
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            db_path = str(DB_PATH)
        self.db_path = db_path
        self._init_database()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA foreign_keys=ON')
        return conn

    def _init_database(self) -> None:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute('''
                CREATE TABLE IF NOT EXISTS usage_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    app_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    duration_seconds REAL NOT NULL,
                    session_count INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS alert_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    category TEXT NOT NULL,
                    alert_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    message TEXT
                )''')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_usage_date ON usage_records(date)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_usage_app ON usage_records(app_name)')

            # Schema 迁移
            cur.execute(
                'CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY)')
            row = cur.execute('SELECT version FROM schema_version').fetchone()
            current = row[0] if row else 0
            if current < CURRENT_SCHEMA_VERSION:
                self._migrate(conn, current, CURRENT_SCHEMA_VERSION)
            conn.commit()

    def _migrate(self, conn: sqlite3.Connection, from_ver: int, to_ver: int) -> None:
        cur = conn.cursor()
        for v in range(from_ver, to_ver):
            if v == 0:
                # v0 → v1: 新增 ignored_apps / custom_categories / app_category_rules
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS ignored_apps (
                        exe_path TEXT PRIMARY KEY,
                        app_name TEXT NOT NULL,
                        ignored_at TEXT NOT NULL)''')
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS custom_categories (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL UNIQUE,
                        color TEXT DEFAULT '#0078D4',
                        created_at TEXT NOT NULL)''')
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS app_category_rules (
                        exe_path TEXT NOT NULL,
                        category_id TEXT NOT NULL,
                        FOREIGN KEY (category_id) REFERENCES custom_categories(id),
                        PRIMARY KEY (exe_path, category_id))''')
            # usage_records 新增 exe_path 列（v0 数据可能没有）
            try:
                cur.execute('ALTER TABLE usage_records ADD COLUMN exe_path TEXT')
            except sqlite3.OperationalError:
                pass  # 列已存在

        conn.execute('INSERT OR REPLACE INTO schema_version VALUES (?)', (to_ver,))
        logger.info('数据库迁移: v%d → v%d', from_ver, to_ver)

    # ---- 基础 CRUD ----

    def save_session(self, app_name: str, category: str,
                     duration_seconds: float, record_date: str | None = None,
                     exe_path: str = '') -> None:
        if record_date is None:
            record_date = date.today().isoformat()
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                'SELECT id, duration_seconds, session_count FROM usage_records '
                'WHERE date = ? AND app_name = ?', (record_date, app_name))
            existing = cur.fetchone()
            if existing:
                rid, old_dur, old_cnt = existing
                cur.execute(
                    'UPDATE usage_records SET duration_seconds = ?, session_count = ? WHERE id = ?',
                    (old_dur + duration_seconds, old_cnt + 1, rid))
            else:
                cur.execute(
                    'INSERT INTO usage_records (date, app_name, category, duration_seconds, exe_path) '
                    'VALUES (?, ?, ?, ?, ?)',
                    (record_date, app_name, category, duration_seconds, exe_path))
            conn.commit()

    def save_alert(self, category: str, message: str,
                   alert_date: str | None = None) -> None:
        if alert_date is None:
            alert_date = date.today().isoformat()
        with self._get_conn() as conn:
            conn.execute(
                'INSERT INTO alert_records (date, category, message) VALUES (?, ?, ?)',
                (alert_date, category, message))
            conn.commit()

    def get_daily_usage(self, query_date: str | None = None) -> list[DailyUsage]:
        if query_date is None:
            query_date = date.today().isoformat()
        with self._get_conn() as conn:
            rows = conn.execute(
                'SELECT date, app_name, category, duration_seconds, session_count, COALESCE(exe_path, "") '
                'FROM usage_records WHERE date = ? ORDER BY duration_seconds DESC',
                (query_date,)).fetchall()
        return [DailyUsage(date=r[0], app_name=r[1], category=r[2],
                           duration_seconds=r[3], session_count=r[4], exe_path=r[5]) for r in rows]

    def get_daily_report(self, query_date: str | None = None) -> DailyReport | None:
        if query_date is None:
            query_date = (date.today() - timedelta(days=1)).isoformat()
        records = self.get_daily_usage(query_date)
        if not records:
            return None
        total = browser = game = other = 0.0
        app_breakdown: dict[str, float] = {}
        cat_breakdown: dict[str, float] = {}
        for r in records:
            total += r.duration_seconds
            app_breakdown[r.app_name] = r.duration_seconds
            cat_breakdown[r.category] = cat_breakdown.get(r.category, 0.0) + r.duration_seconds
            if r.category == 'browser':
                browser += r.duration_seconds
            elif r.category == 'game':
                game += r.duration_seconds
            else:
                other += r.duration_seconds
        with self._get_conn() as conn:
            alerts = conn.execute(
                'SELECT COUNT(*) FROM alert_records WHERE date = ?',
                (query_date,)).fetchone()[0]
        return DailyReport(
            date=query_date, total_usage_seconds=total,
            browser_seconds=browser, game_seconds=game, other_seconds=other,
            app_breakdown=app_breakdown, category_breakdown=cat_breakdown,
            alerts_triggered=alerts)

    def get_date_range_reports(self, start_date: str, end_date: str) -> list[DailyReport]:
        reports = []
        current = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        while current <= end:
            report = self.get_daily_report(current.isoformat())
            if report:
                reports.append(report)
            current += timedelta(days=1)
        return reports

    def get_daily_game_detail(self, query_date: str | None = None) -> list[dict]:
        if query_date is None:
            query_date = date.today().isoformat()
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT app_name, category, SUM(duration_seconds) "
                "FROM usage_records WHERE date = ? GROUP BY app_name, category "
                "ORDER BY SUM(duration_seconds) DESC", (query_date,)).fetchall()
        app_map: dict[str, dict] = {}
        for app, cat, secs in rows:
            if app not in app_map:
                app_map[app] = {'app_name': app, 'game': 0.0, 'browser': 0.0, 'other': 0.0}
            if cat in app_map[app]:
                app_map[app][cat] = float(secs or 0)
        return list(app_map.values())

    def get_week_category_data(self, start_date: str, end_date: str) -> list[dict]:
        result = []
        current = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        with self._get_conn() as conn:
            while current <= end:
                d = current.isoformat()
                rows = conn.execute(
                    "SELECT category, SUM(duration_seconds) FROM usage_records "
                    "WHERE date = ? GROUP BY category", (d,)).fetchall()
                day_data: dict[str, float] = {'date': d, 'game': 0.0, 'browser': 0.0, 'other': 0.0}
                for cat, secs in rows:
                    if cat in day_data:
                        day_data[cat] = float(secs or 0)
                result.append(day_data)
                current += timedelta(days=1)
        return result

    def get_monthly_weekday_data(self, year: int, month: int) -> dict:
        import calendar
        today = date.today()
        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])
        chart_end = min(last_day, today - timedelta(days=1))

        month_rows: dict[str, dict[str, float]] = {}
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT date, category, SUM(duration_seconds) "
                "FROM usage_records WHERE date >= ? AND date <= ? "
                "GROUP BY date, category",
                (first_day.isoformat(), chart_end.isoformat())).fetchall()
        for d, cat, secs in rows:
            if d not in month_rows:
                month_rows[d] = {'game': 0.0, 'browser': 0.0, 'other': 0.0}
            if cat in month_rows[d]:
                month_rows[d][cat] = float(secs or 0)

        week_start_of_month = first_day - timedelta(days=first_day.weekday())
        prev_rows: dict[str, dict[str, float]] = {}
        if week_start_of_month < first_day:
            prev_first = (first_day - timedelta(days=1)).replace(day=1)
            prev_last = first_day - timedelta(days=1)
            with self._get_conn() as conn:
                prev = conn.execute(
                    "SELECT date, category, SUM(duration_seconds) "
                    "FROM usage_records WHERE date >= ? AND date <= ? "
                    "GROUP BY date, category",
                    (prev_first.isoformat(), prev_last.isoformat())).fetchall()
            for d, cat, secs in prev:
                if d not in prev_rows:
                    prev_rows[d] = {'game': 0.0, 'browser': 0.0, 'other': 0.0}
                if cat in prev_rows[d]:
                    prev_rows[d][cat] = float(secs or 0)

        day_map = {**prev_rows, **month_rows}
        wd_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        weekday_bars: dict[int, list[dict]] = {i: [] for i in range(7)}
        wd_counter = [0] * 7
        cur = first_day
        while cur <= chart_end:
            wd = cur.weekday()
            wd_counter[wd] += 1
            dd = cur.isoformat()
            dd_data = day_map.get(dd)
            if dd_data is not None:
                weekday_bars[wd].append({
                    'label': f'{cur.month}/{cur.day}', 'week_idx': wd_counter[wd],
                    'game': dd_data['game'], 'browser': dd_data['browser'],
                    'other': dd_data['other']})
            cur += timedelta(days=1)

        week_bars = []
        for wi in range(6):
            ws = week_start_of_month + timedelta(weeks=wi)
            we = ws + timedelta(days=6)
            if ws > chart_end:
                break
            has_data = any(d.isoformat() in day_map for d in
                           (ws + timedelta(days=i) for i in range(7) if ws + timedelta(days=i) <= chart_end))
            if not has_data:
                continue
            we_safe = min(we, chart_end)
            total: dict[str, float] = {'game': 0.0, 'browser': 0.0, 'other': 0.0}
            c2 = ws
            while c2 <= we_safe:
                dd_data = day_map.get(c2.isoformat(), {'game': 0.0, 'browser': 0.0, 'other': 0.0})
                for k in total:
                    total[k] += dd_data[k]
                c2 += timedelta(days=1)
            week_bars.append({
                'label': f'第{wi+1}周({ws.month}/{ws.day}-{we_safe.month}/{we_safe.day})',
                'week_start': ws.isoformat(), **total})
        return {'weekday_bars': weekday_bars, 'week_bars': week_bars}

    # ---- 新增功能 ----

    @staticmethod
    def format_duration(seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f'{hours}小时{minutes}分钟' if hours else f'{minutes}分钟'

    def get_database_size(self) -> int:
        """返回数据库文件大小（字节）"""
        try:
            return os.path.getsize(self.db_path)
        except OSError:
            return 0

    def export_to_csv(self, output_path: str, start_date: str | None = None,
                      end_date: str | None = None) -> int:
        """导出使用记录到 CSV，返回导出行数"""
        if start_date is None:
            start_date = '2000-01-01'
        if end_date is None:
            end_date = date.today().isoformat()
        with self._get_conn() as conn:
            rows = conn.execute(
                'SELECT date, app_name, category, duration_seconds, session_count '
                'FROM usage_records WHERE date >= ? AND date <= ? ORDER BY date, duration_seconds DESC',
                (start_date, end_date)).fetchall()
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['日期', '应用', '分类', '时长(秒)', '会话数', '时长(可读)'])
            for r in rows:
                writer.writerow([r[0], r[1], r[2], r[3], r[4], self.format_duration(r[3])])
        return len(rows)

    def cleanup_expired_data(self, retention_policy: str) -> int:
        """按保留策略清理过期数据，返回删除行数"""
        if retention_policy == 'unlimited':
            return 0
        today = date.today()
        if retention_policy == '1month':
            cutoff = (today - timedelta(days=30)).isoformat()
        elif retention_policy == '3months':
            cutoff = (today - timedelta(days=90)).isoformat()
        elif retention_policy == '1year':
            cutoff = (today - timedelta(days=365)).isoformat()
        else:
            return 0
        with self._get_conn() as conn:
            cur = conn.execute(
                'DELETE FROM usage_records WHERE date < ?', (cutoff,))
            conn.execute(
                'DELETE FROM alert_records WHERE date < ?', (cutoff,))
            conn.commit()
            deleted = cur.rowcount
        if deleted > 0:
            logger.info('清理了 %d 条过期记录（%s 之前）', deleted, cutoff)
        return deleted

    # ---- 忽略应用 ----

    def add_ignored_app(self, exe_path: str, app_name: str) -> None:
        import datetime
        with self._get_conn() as conn:
            conn.execute(
                'INSERT OR REPLACE INTO ignored_apps VALUES (?, ?, ?)',
                (exe_path, app_name, datetime.datetime.now().isoformat()))
            conn.commit()

    def remove_ignored_app(self, exe_path: str) -> None:
        with self._get_conn() as conn:
            conn.execute('DELETE FROM ignored_apps WHERE exe_path = ?', (exe_path,))
            conn.commit()

    def get_all_ignored_apps(self) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute('SELECT exe_path, app_name, ignored_at FROM ignored_apps').fetchall()
        return [{'exe_path': r[0], 'app_name': r[1], 'ignored_at': r[2]} for r in rows]
