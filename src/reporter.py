"""
报告生成模块（多主题）
- 日报 / 周报 / 月报
- 从 CSS 文件加载主题样式
- Chart.js 图表配色跟随主题
"""

import json
import logging
import os
import webbrowser
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from .data_store import DataStore, DailyReport
from .i18n import t

logger = logging.getLogger(__name__)

# ---- 工具函数 ----

def _fmt_h(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    return f'{h}h{m}m' if h else f'{m}m'


def _fmt_h_full(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    return t('report.time_h', h=h, m=m) if h else t('report.time_m', m=m)


# ---- 主题配置 ----

class Theme:
    """主题配置"""
    def __init__(self, name: str, display_name: str, css_file: str,
                 chart_font: str, cat_colors: dict[str, str],
                 header_icon: str = ''):
        self.name = name
        self.display_name = display_name
        self.css_file = css_file
        self.chart_font = chart_font
        self.cat_colors = cat_colors  # category -> hex color
        self.header_icon = header_icon


# 图表图例通用配置生成器
def _make_legend_opts(chart_font: str, hidden: bool = False) -> str:
    size = 12 if hidden else 13
    return json.dumps({
        'position': 'top',
        'labels': {
            'font': {'family': chart_font, 'size': size},
            'color': '#ffffff' if 'Segoe UI' in chart_font and not hidden else '#5a3e2b',
            'usePointStyle': True, 'pointStyleWidth': 14 if not hidden else 12,
            'padding': 16 if not hidden else 14,
            'boxHeight': 10 if not hidden else 9, 'boxWidth': 14 if not hidden else 12,
        }
    }, ensure_ascii=False)


def _get_chart_font(theme_name: str) -> str:
    fonts = {
        'minimal': "-apple-system, 'Segoe UI', sans-serif",
        'fairy_tale': "'Crimson Pro', 'Palatino Linotype', 'Book Antiqua', serif",
        'business': "'Segoe UI', sans-serif",
    }
    return fonts.get(theme_name, fonts['fairy_tale'])


def _get_legend_text_color(theme_name: str) -> str:
    return '#e8e8e8' if theme_name == 'business' else '#5a3e2b'


def _get_cat_colors(theme_name: str) -> dict[str, str]:
    colors = {
        'minimal': {'browser': '#42a5f5', 'game': '#ef5350', 'other': '#78909c'},
        'fairy_tale': {'browser': '#5b8ec9', 'game': '#d45d5d', 'other': '#9e8070'},
        'business': {'browser': '#4361ee', 'game': '#e94560', 'other': '#8892a4'},
    }
    return colors.get(theme_name, colors['fairy_tale'])


def _get_game_palette(theme_name: str) -> list[str]:
    if theme_name == 'business':
        return ['#e94560', '#00d2ff', '#7b2cbf', '#00b4d8', '#3a86ff',
                '#f77f00', '#80ed99', '#ff006e', '#8338ec', '#ffbe0b']
    if theme_name == 'minimal':
        return ['#ef5350', '#ff7043', '#ffa726', '#66bb6a', '#42a5f5',
                '#ab47bc', '#ec407a', '#26a69a', '#8d6e63', '#78909c']
    return ['#d45d5d', '#e87c5c', '#c9963c', '#9b7fbf', '#5bb9a0',
            '#e8a0b4', '#5b8ec9', '#8fa84e', '#d4855a', '#7ab8c4']


def _get_header_icon(theme_name: str) -> str:
    return {'fairy_tale': '✨', 'minimal': '', 'business': '📊'}.get(theme_name, '')


def _get_weekday_names() -> list[str]:
    return t('report.weekday_names').split(',')


# ---- HTML 报告生成器 ----

class HTMLReportGenerator:
    """HTML 报告生成器（多主题）"""

    def __init__(self, output_dir: str | None = None):
        if output_dir is None:
            from .constants import REPORT_DIR
            self.output_dir = REPORT_DIR
        else:
            self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._data_store: DataStore | None = None
        self._theme_css_cache: dict[str, str] = {}

    def set_data_store(self, store: DataStore) -> None:
        self._data_store = store

    def _get_chartjs(self) -> str:
        """读取本地 Chart.js，内嵌到 HTML（离线可用）"""
        candidates = [
            Path(__file__).parent.parent / 'assets' / 'chart.umd.min.js',
        ]
        for p in candidates:
            if p.exists():
                try:
                    return f'<script>{p.read_text(encoding="utf-8")}</script>'
                except Exception:
                    pass
        # 兜底：CDN
        return '<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>'

    def _get_css(self, theme: str) -> str:
        """加载主题 CSS 文件"""
        if theme in self._theme_css_cache:
            return self._theme_css_cache[theme]
        css_file = Path(__file__).parent.parent / 'assets' / 'themes' / f'{theme}.css'
        if css_file.exists():
            css = css_file.read_text(encoding='utf-8')
        else:
            css = ''
            logger.warning('主题 CSS 文件不存在: %s', css_file)
        self._theme_css_cache[theme] = css
        return css

    # ---- 日报 ----

    def generate_daily_report(self, report: DailyReport, theme: str = 'fairy_tale') -> str:
        css = self._get_css(theme)
        chartjs_tag = self._get_chartjs()
        cat_colors = _get_cat_colors(theme)
        game_palette = _get_game_palette(theme)
        chart_font = _get_chart_font(theme)
        legend_text_color = _get_legend_text_color(theme)
        header_icon = _get_header_icon(theme)

        # 动态标题
        today = date.today()
        yesterday = today - timedelta(days=1)
        try:
            report_date = date.fromisoformat(report.date)
        except Exception:
            report_date = today
        if report_date == yesterday:
            header_title = t('report.daily_title_yesterday', icon=header_icon)
        else:
            header_title = t('report.daily_title_date', icon=header_icon,
                              month=report_date.month, day=report_date.day)

        def pct(s, total):
            return f'{s/total*100:.1f}%' if total else '0%'

        cat_names = {'browser': t('report.category_browser'),
                     'game': t('report.category_game'),
                     'other': t('report.category_other')}
        cat_html = ''
        for cat, secs in report.category_breakdown.items():
            color = cat_colors.get(cat, '#9e8070')
            cat_html += f"""<div class="cat-item"><div class="cat-dot" style="background:{color}"></div><div class="cat-info"><span class="cat-name">{cat_names.get(cat, cat)}</span><span class="cat-time time-num">{_fmt_h_full(secs)}</span><span class="cat-pct">{pct(secs, report.total_usage_seconds)}</span></div></div>"""

        app_rows = ''
        app_to_cat: dict[str, str] = {}
        app_exe_map: dict[str, str] = {}
        if self._data_store:
            for rec in self._data_store.get_daily_usage(report.date):
                app_to_cat[rec.app_name] = rec.category
                app_exe_map[rec.app_name] = rec.exe_path
        for app, secs in sorted(report.app_breakdown.items(), key=lambda x: x[1], reverse=True):
            cat_key = app_to_cat.get(app, 'other')
            exe = app_exe_map.get(app, '')
            safe_app = app.replace('\\', '\\\\').replace("'", "\\'")
            safe_exe = exe.replace('\\', '\\\\').replace("'", "\\'")
            app_rows += f"""<tr><td>{app}</td><td class="time-num">{_fmt_h_full(secs)}</td><td><div class="prog-wrap"><div class="prog-fill" style="width:{pct(secs,report.total_usage_seconds)};background:{cat_colors.get(cat_key, '#9e8070')}"></div></div></td><td class="time-num">{pct(secs, report.total_usage_seconds)}</td><td class="ignore-td"><button class="ignore-btn" onclick="ignoreApp('{safe_app}','{safe_exe}',this)" title="{t('report.ignore_btn')}">✕</button></td></tr>"""

        game_detail = []
        if self._data_store:
            game_detail = self._data_store.get_daily_game_detail(report.date)
        game_items_html = ''
        game_chart_labels = '[]'
        game_chart_datasets = '[]'
        game_apps = sorted([g for g in game_detail if g['game'] > 0], key=lambda x: x['game'], reverse=True)

        if game_apps:
            _g_labels = [g['app_name'] for g in game_apps]
            _g_hours = [round(g['game'] / 3600, 2) for g in game_apps]
            _g_colors = [game_palette[i % len(game_palette)] for i in range(len(game_apps))]
            game_chart_labels = json.dumps(_g_labels, ensure_ascii=False)
            game_chart_datasets = json.dumps([{
                'label': t('report.game_duration'), 'data': _g_hours,
                'backgroundColor': _g_colors, 'borderRadius': 6,
            }], ensure_ascii=False)
            for i, g in enumerate(game_apps):
                color = game_palette[i % len(game_palette)]
                game_items_html += f"""<div class="game-item"><div class="game-icon" style="background:{color}22; color:{color}">✦</div><span class="game-name">{g['app_name']}</span><span class="game-time">{_fmt_h_full(g['game'])}</span></div>"""

        bh = round(report.browser_seconds / 3600, 2)
        gh = round(report.game_seconds / 3600, 2)
        oh = round(report.other_seconds / 3600, 2)
        lbl_browser = t('report.browser')
        lbl_game = t('report.game')
        lbl_other = t('report.category_other')
        cat_bar_labels = json.dumps([lbl_browser, lbl_game, lbl_other], ensure_ascii=False)
        cat_bar_datasets = json.dumps([
            {'label': lbl_browser, 'data': [bh, 0, 0], 'backgroundColor': cat_colors['browser'] + 'd1', 'borderRadius': 5},
            {'label': lbl_game, 'data': [0, gh, 0], 'backgroundColor': cat_colors['game'] + 'd1', 'borderRadius': 5},
            {'label': lbl_other, 'data': [0, 0, oh], 'backgroundColor': cat_colors['other'] + 'bf', 'borderRadius': 5},
        ], ensure_ascii=False)
        legend_opts = _make_legend_opts(chart_font, hidden=True)
        tooltip_cb = 'ctx => ctx.raw > 0 ? " " + ctx.dataset.label + ": " + ctx.raw + "h" : null'
        filter_cb = 'item => item.raw > 0'
        js_chart_font = json.dumps(chart_font, ensure_ascii=False)
        duration_h = t('report.duration_h')

        html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{t('report.page_title', date=report.date)}</title>
{chartjs_tag}
<style>{css}</style><style>.chart-wrap {{ height:240px; }} .game-chart-wrap {{ height:200px; }}
.ignore-btn {{ border:none; background:#e8d4d4; color:#c05050; border-radius:50%; width:22px; height:22px; cursor:pointer; font-size:12px; display:inline-flex; align-items:center; justify-content:center; transition:background .2s; }}
.ignore-btn:hover {{ background:#d45d5d; color:#fff; }}</style>
</head><body><div class="container">
<div class="header"><h1>{header_title}</h1><div class="subtitle">{report.date}</div></div>
<div class="summary">
<div class="card total"><div class="lbl">{t('report.total')}</div><div class="val">{_fmt_h_full(report.total_usage_seconds)}</div></div>
<div class="card browser"><div class="lbl">{lbl_browser}</div><div class="val">{_fmt_h_full(report.browser_seconds)}</div></div>
<div class="card game"><div class="lbl">{lbl_game}</div><div class="val">{_fmt_h_full(report.game_seconds)}</div></div>
<div class="card alert"><div class="lbl">{t('report.alerts')}</div><div class="val">{t('report.alerts_times', count=report.alerts_triggered)}</div></div>
</div>
<div class="section"><h2>{t('report.category_distribution')}</h2><div class="chart-wrap"><canvas id="catChart"></canvas></div></div>
<div class="section"><h2>{t('report.category_detail')}</h2><div class="cat-list">{cat_html}</div></div>
{('<div class="section"><h2>' + t('report.game_breakdown') + '</h2><div class="game-chart-wrap"><canvas id="gameChart"></canvas></div><div class="game-list" style="margin-top:12px">' + game_items_html + '</div></div>') if game_apps else ''}
<div class="section"><h2>{t('report.app_detail')}</h2><table><thead><tr><th>{t('report.app_col')}</th><th>{t('report.duration_col')}</th><th>{t('report.proportion_col')}</th><th>{t('report.percent_col')}</th><th>{t('report.action_col')}</th></tr></thead><tbody>{app_rows}</tbody></table></div>
<div class="footer">{t('report.generated_by')}</div>
</div><script>
new Chart(document.getElementById('catChart'), {{
    type:'bar', data:{{ labels:{cat_bar_labels}, datasets:{cat_bar_datasets} }},
    options:{{ responsive:true, maintainAspectRatio:false, indexAxis:'y',
        plugins:{{ legend:{{ display:false }},
            tooltip:{{ callbacks:{{ label:{tooltip_cb}, filter:{filter_cb} }} }}
        }},
        scales:{{ x:{{ beginAtZero:true, title:{{ display:true, text:'{duration_h}', font:{{ family:{js_chart_font}, size:12 }} }},
            ticks:{{ font:{{ family:{js_chart_font} }}, callback: v => v+'h' }} }},
            y:{{ ticks:{{ font:{{ family:{js_chart_font}, size:13 }} }} }}
        }}
    }}
}});
{f"""new Chart(document.getElementById('gameChart'), {{
    type:'bar', data:{{ labels:{game_chart_labels}, datasets:{game_chart_datasets} }},
    options:{{ indexAxis:'y', responsive:true, maintainAspectRatio:false,
        plugins:{{ legend:{legend_opts}, tooltip:{{ callbacks:{{ label: ctx => ' '+ctx.raw+'h' }} }} }},
        scales:{{ x:{{ beginAtZero:true, title:{{ display:true, text:'{duration_h}', font:{{ family:{js_chart_font}, size:12 }} }},
            ticks:{{ font:{{ family:{js_chart_font} }}, callback: v => v+'h' }} }},
            y:{{ ticks:{{ font:{{ family:{js_chart_font}, size:12 }} }} }}
        }}
    }}
}});""" if game_apps else ''}
function ignoreApp(app,exe,btn){{
  btn.disabled=true; btn.textContent='…'; btn.style.opacity='.5';
  fetch('http://127.0.0.1:19234/ignore',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{app_name:app,exe_path:exe}})}})
  .then(r=>r.json()).then(d=>{{
    if(d.ok){{ var tr=btn.closest('tr'); tr.style.opacity='.4'; tr.style.textDecoration='line-through'; btn.textContent='✓'; btn.style.background='#b8d8b8'; btn.style.color='#4a8a4a'; }}
    else{{ btn.disabled=false; btn.textContent='✕'; btn.style.opacity='1'; alert(d.msg||'Error'); }}
  }}).catch(()=>{{ btn.disabled=false; btn.textContent='✕'; btn.style.opacity='1'; alert('{t("report.connect_failed")}'); }});
}}
</script></body></html>"""
        return self._write_report(f'usage_report_{report.date}.html', html)

    # ---- 周报 ----

    def generate_weekly_report(self, week_start: str, week_end: str,
                               theme: str = 'fairy_tale') -> str:
        css = self._get_css(theme)
        chartjs_tag = self._get_chartjs()
        cat_colors = _get_cat_colors(theme)
        chart_font = _get_chart_font(theme)
        js_chart_font = json.dumps(chart_font, ensure_ascii=False)
        legend_opts = _make_legend_opts(chart_font)
        header_icon = _get_header_icon(theme)

        day_data = self._data_store.get_week_category_data(week_start, week_end)
        wd_names = _get_weekday_names()
        labels = [f'{wd_names[i]}\n{d["date"][-5:].replace("-","/")}' for i, d in enumerate(day_data)]
        game_h = [round(d['game'] / 3600, 2) for d in day_data]
        browser_h = [round(d['browser'] / 3600, 2) for d in day_data]
        other_h = [round(d['other'] / 3600, 2) for d in day_data]
        total_game = sum(d['game'] for d in day_data)
        total_browser = sum(d['browser'] for d in day_data)
        total_other = sum(d['other'] for d in day_data)
        total_all = total_game + total_browser + total_other

        lbl_browser = t('report.browser')
        lbl_game = t('report.game')
        lbl_other = t('report.category_other')

        day_rows = ''
        for i, d in enumerate(day_data):
            total = d['game'] + d['browser'] + d['other']
            day_rows += f"""<tr><td>{wd_names[i]}</td><td>{d['date']}</td><td style="color:{cat_colors['game']}">{_fmt_h(d['game'])}</td><td style="color:{cat_colors['browser']}">{_fmt_h(d['browser'])}</td><td style="color:{cat_colors['other']}">{_fmt_h(d['other'])}</td><td><strong>{_fmt_h(total)}</strong></td></tr>"""

        js_labels = json.dumps(labels, ensure_ascii=False)
        js_datasets = json.dumps([
            {'label': lbl_game, 'data': game_h, 'backgroundColor': cat_colors['game'] + 'd1'},
            {'label': lbl_browser, 'data': browser_h, 'backgroundColor': cat_colors['browser'] + 'd1'},
            {'label': lbl_other, 'data': other_h, 'backgroundColor': cat_colors['other'] + 'c2'},
        ], ensure_ascii=False)
        tooltip_cb = "ctx => ' ' + ctx.dataset.label + ': ' + ctx.raw + 'h'"

        html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{t('report.weekly_page_title', start=week_start, end=week_end)}</title>
{chartjs_tag}
<style>{css}</style><style>.chart-wrap {{ height:300px; }}</style></head>
<body><div class="container">
<div class="header"><h1>{t('report.weekly_title', icon=header_icon)}</h1><div class="subtitle">{week_start} ～ {week_end}</div></div>
<div class="summary">
<div class="card total"><div class="lbl">{t('report.week_total')}</div><div class="val">{_fmt_h(total_all)}</div></div>
<div class="card game"><div class="lbl">{lbl_game}</div><div class="val">{_fmt_h(total_game)}</div></div>
<div class="card browser"><div class="lbl">{lbl_browser}</div><div class="val">{_fmt_h(total_browser)}</div></div>
<div class="card other"><div class="lbl">{lbl_other}</div><div class="val">{_fmt_h(total_other)}</div></div>
</div>
<div class="section"><h2>{t('report.daily_distribution')}</h2><div class="chart-wrap"><canvas id="weekChart"></canvas></div></div>
<div class="section"><h2>{t('report.daily_detail')}</h2><table><thead><tr><th>{t('report.weekday_col')}</th><th>{t('report.date_col')}</th><th>{lbl_game}</th><th>{lbl_browser}</th><th>{lbl_other}</th><th>{t('report.total_col')}</th></tr></thead><tbody>{day_rows}</tbody></table></div>
<div class="footer">{t('report.generated_by')}</div>
</div><script>
new Chart(document.getElementById('weekChart'), {{
    type:'bar', data:{{ labels:{js_labels}, datasets:{js_datasets} }},
    options:{{ responsive:true, maintainAspectRatio:false,
        plugins:{{ legend:{legend_opts}, tooltip:{{ mode:'index', intersect:false, callbacks:{{ label:{tooltip_cb} }} }} }},
        scales:{{ x:{{ stacked:true, title:{{ display:true, text:'{t("report.date_label")}', font:{{ family:{js_chart_font}, size:12 }} }},
            ticks:{{ font:{{ family:{js_chart_font} }} }} }},
            y:{{ stacked:true, beginAtZero:true, title:{{ display:true, text:'{t("report.duration_h")}', font:{{ family:{js_chart_font}, size:12 }} }},
            ticks:{{ font:{{ family:{js_chart_font} }}, callback: v => v+'h' }} }}
        }}
    }}
}});
</script></body></html>"""
        return self._write_report(f'weekly_report_{week_start}_to_{week_end}.html', html)

    # ---- 月报 ----

    def generate_monthly_report(self, year: int, month: int,
                                theme: str = 'fairy_tale') -> str:
        css = self._get_css(theme)
        chartjs_tag = self._get_chartjs()
        cat_colors = _get_cat_colors(theme)
        chart_font = _get_chart_font(theme)
        js_chart_font = json.dumps(chart_font, ensure_ascii=False)
        legend_opts = _make_legend_opts(chart_font)
        header_icon = _get_header_icon(theme)

        lang = self._get_current_lang()
        if lang == 'en':
            month_str = f'{year}/{month:02d}'
        else:
            month_str = f'{year}年{month}月'

        data = self._data_store.get_monthly_weekday_data(year, month)
        wd_bars = data['weekday_bars']
        week_bars = data['week_bars']
        wd_names = _get_weekday_names()

        lbl_browser = t('report.browser')
        lbl_game = t('report.game')
        lbl_other = t('report.category_other')
        duration_h = t('report.duration_h')

        wd_game_h = [round(sum(x['game'] for x in wd_bars[wd]) / 3600, 2) for wd in range(7)]
        wd_browser_h = [round(sum(x['browser'] for x in wd_bars[wd]) / 3600, 2) for wd in range(7)]
        wd_other_h = [round(sum(x['other'] for x in wd_bars[wd]) / 3600, 2) for wd in range(7)]
        wchart_labels = json.dumps(wd_names, ensure_ascii=False)
        js_wd_datasets = json.dumps([
            {'label': lbl_game, 'data': wd_game_h, 'backgroundColor': cat_colors['game'] + 'cc'},
            {'label': lbl_browser, 'data': wd_browser_h, 'backgroundColor': cat_colors['browser'] + 'cc'},
            {'label': lbl_other, 'data': wd_other_h, 'backgroundColor': cat_colors['other'] + 'b3'},
        ], ensure_ascii=False)

        wd_occ_datasets = []
        wd_occ_titles = []
        for wd in range(7):
            items = wd_bars[wd]
            if not items:
                continue
            wd_occ_datasets.append(json.dumps([
                {'label': lbl_game, 'data': [round(it['game']/3600, 2) for it in items], 'backgroundColor': cat_colors['game'] + 'cc'},
                {'label': lbl_browser, 'data': [round(it['browser']/3600, 2) for it in items], 'backgroundColor': cat_colors['browser'] + 'cc'},
                {'label': lbl_other, 'data': [round(it['other']/3600, 2) for it in items], 'backgroundColor': cat_colors['other'] + 'b3'},
            ], ensure_ascii=False))
            wd_occ_titles.append(json.dumps([it['label'] for it in items], ensure_ascii=False))

        week_labels = json.dumps([w['label'] for w in week_bars], ensure_ascii=False)
        week_datasets = json.dumps([
            {'label': lbl_game, 'data': [round(w['game']/3600, 2) for w in week_bars], 'backgroundColor': cat_colors['game'] + 'cc'},
            {'label': lbl_browser, 'data': [round(w['browser']/3600, 2) for w in week_bars], 'backgroundColor': cat_colors['browser'] + 'cc'},
            {'label': lbl_other, 'data': [round(w['other']/3600, 2) for w in week_bars], 'backgroundColor': cat_colors['other'] + 'b3'},
        ], ensure_ascii=False)

        total_game_m = sum(w['game'] for w in week_bars)
        total_browser_m = sum(w['browser'] for w in week_bars)
        total_other_m = sum(w['other'] for w in week_bars)
        total_all_m = total_game_m + total_browser_m + total_other_m

        wd_colors_arr = [cat_colors['game'], cat_colors['browser'], '#5bb9a0', cat_colors['game'], cat_colors['other'], '#e8a0b4', '#9b7fbf']
        # 星期缩写（用于月报卡片）
        wd_short = wd_names if not wd_names[0].startswith('周') else [n[-1] for n in wd_names]
        wd_cards = ''
        for wd in range(7):
            g = sum(x['game'] for x in wd_bars[wd])
            b = sum(x['browser'] for x in wd_bars[wd])
            o = sum(x['other'] for x in wd_bars[wd])
            total = g + b + o
            if total <= 0:
                continue
            wd_cards += f"""<div class="wd-card" style="border-left-color:{wd_colors_arr[wd]}"><div class="wd-name">{wd_names[wd]}</div><div class="wd-total">{_fmt_h(total)}</div><div class="wd-sub"><span style="color:{cat_colors['game']}">{_fmt_h(g)}</span> · <span style="color:{cat_colors['browser']}">{_fmt_h(b)}</span> · <span style="color:{cat_colors['other']}">{_fmt_h(o)}</span></div></div>"""

        week_table_rows = ''
        for w in week_bars:
            total = w['game'] + w['browser'] + w['other']
            week_table_rows += f"""<tr><td>{w['label']}</td><td style="color:{cat_colors['game']}">{_fmt_h(w['game'])}</td><td style="color:{cat_colors['browser']}">{_fmt_h(w['browser'])}</td><td style="color:{cat_colors['other']}">{_fmt_h(w['other'])}</td><td><strong>{_fmt_h(total)}</strong></td></tr>"""

        wd_occ_subcharts = ''
        for idx in range(len(wd_occ_datasets)):
            wd_occ_subcharts += f'<div class="wd-occ-panel"><div class="wd-occ-title">{wd_names[idx]}</div><div class="chart-wrap wd-occ-chart"><canvas id="wdOccChart{idx}"></canvas></div></div>'

        wd_occ_js = ''
        for idx in range(len(wd_occ_datasets)):
            wd_occ_js += f"""new Chart(document.getElementById('wdOccChart{idx}'), {{
    type:'bar', data:{{ labels:{wd_occ_titles[idx]}, datasets:{wd_occ_datasets[idx]} }},
    options:{{ responsive:true, maintainAspectRatio:false,
        plugins:{{ legend:{{ display:false }},
            tooltip:{{ callbacks:{{ label: ctx => ' '+ctx.dataset.label+': '+ctx.raw+'h' }} }} }},
        scales:{{ x:{{ }}, y:{{ beginAtZero:true, ticks:{{ callback: v => v+'h' }} }} }}
    }}
}});"""

        week_mini_html = ''.join(
            f'<div class="week-mini"><div class="week-mini-label">{w["label"]}</div>'
            f'<div class="week-mini-total">{_fmt_h(w["game"]+w["browser"]+w["other"])}</div>'
            f'<div class="week-mini-sub"><span style="color:{cat_colors["game"]}">{_fmt_h(w["game"])}</span> · '
            f'<span style="color:{cat_colors["browser"]}">{_fmt_h(w["browser"])}</span> · '
            f'<span style="color:{cat_colors["other"]}">{_fmt_h(w["other"])}</span></div></div>'
            for w in week_bars)

        tooltip_cb = "ctx => ' ' + ctx.dataset.label + ': ' + ctx.raw + 'h'"

        html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{t('report.monthly_page_title', month_str=month_str)}</title>
{chartjs_tag}
<style>{css}</style>
<style>.chart-wrap {{ height:260px; }}
.wd-occ-grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(200px,1fr)); gap:14px; margin-top:4px; }}
.wd-occ-panel {{ background:var(--g-bg); border-radius:var(--g-radius-sm); border:1px solid var(--g-border); padding:12px 10px 8px; }}
.wd-occ-title {{ font-family:var(--g-font); font-size:14px; font-weight:bold; color:var(--g-text); text-align:center; margin-bottom:10px; padding-bottom:6px; border-bottom:1px solid var(--g-border); }}
.wd-occ-chart {{ height:180px; }}
.week-grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(220px,1fr)); gap:10px; margin-top:10px; }}
.week-mini {{ background:var(--g-bg); border:1px solid var(--g-border); border-radius:var(--g-radius-sm); padding:10px 14px; }}
.week-mini-label {{ font-size:12px; color:var(--g-muted); }}
.week-mini-total {{ font-family:var(--g-font); font-size:18px; font-weight:bold; color:var(--g-gold); }}
.week-mini-sub {{ font-size:11px; color:var(--g-muted); margin-top:2px; }}
</style></head><body><div class="container">
<div class="header"><h1>{t('report.monthly_title', icon=header_icon, month_str=month_str)}</h1><div class="subtitle">{t('report.monthly_subtitle')}</div></div>
<div class="summary">
<div class="card total"><div class="lbl">{t('report.month_total')}</div><div class="val">{_fmt_h(total_all_m)}</div></div>
<div class="card game"><div class="lbl">{lbl_game}</div><div class="val">{_fmt_h(total_game_m)}</div></div>
<div class="card browser"><div class="lbl">{lbl_browser}</div><div class="val">{_fmt_h(total_browser_m)}</div></div>
<div class="card other"><div class="lbl">{lbl_other}</div><div class="val">{_fmt_h(total_other_m)}</div></div>
</div>
<div class="section"><h2>{t('report.by_weekday')}</h2><div class="wd-grid">{wd_cards}</div><div class="chart-wrap"><canvas id="weekdaySummaryChart"></canvas></div></div>
<div class="section"><h2>{t('report.weekday_occurrences')}</h2><div class="wd-occ-grid">{wd_occ_subcharts}</div></div>
<div class="section"><h2>{t('report.week_comparison')}</h2><div class="week-grid">{week_mini_html}</div><div class="chart-wrap" style="margin-top:14px"><canvas id="weekChart"></canvas></div>
<table><thead><tr><th>{t('report.week_col')}</th><th>{lbl_game}</th><th>{lbl_browser}</th><th>{lbl_other}</th><th>{t('report.total_col')}</th></tr></thead><tbody>{week_table_rows}</tbody></table></div>
<div class="footer">{t('report.generated_by')}</div>
</div><script>
new Chart(document.getElementById('weekdaySummaryChart'), {{
    type:'bar', data:{{ labels:{wchart_labels}, datasets:{js_wd_datasets} }},
    options:{{ responsive:true, maintainAspectRatio:false,
        plugins:{{ legend:{legend_opts}, tooltip:{{ mode:'index', intersect:false, callbacks:{{ label:{tooltip_cb} }} }} }},
        scales:{{ x:{{ stacked:true, title:{{ display:true, text:'{wd_names[0] if wd_names else ""}', font:{{ family:{js_chart_font}, size:12 }} }},
            ticks:{{ font:{{ family:{js_chart_font} }} }} }},
            y:{{ stacked:true, beginAtZero:true,
                title:{{ display:true, text:'{duration_h}', font:{{ family:{js_chart_font}, size:12 }} }},
                ticks:{{ font:{{ family:{js_chart_font} }}, callback: v => v+'h' }} }}
        }}
    }}
}});
{wd_occ_js}
new Chart(document.getElementById('weekChart'), {{
    type:'bar', data:{{ labels:{week_labels}, datasets:{week_datasets} }},
    options:{{ responsive:true, maintainAspectRatio:false,
        plugins:{{ legend:{legend_opts}, tooltip:{{ mode:'index', intersect:false, callbacks:{{ label:{tooltip_cb} }} }} }},
        scales:{{ x:{{ stacked:true, title:{{ display:true, text:'{t("report.week_col")}', font:{{ family:{js_chart_font}, size:12 }} }},
            ticks:{{ font:{{ family:{js_chart_font} }} }} }},
            y:{{ stacked:true, beginAtZero:true,
                title:{{ display:true, text:'{duration_h}', font:{{ family:{js_chart_font}, size:12 }} }},
                ticks:{{ font:{{ family:{js_chart_font} }}, callback: v => v+'h' }} }}
        }}
    }}
}});
</script></body></html>"""
        return self._write_report(f'monthly_report_{year}_{month:02d}.html', html)

    # ---- 通用 ----

    def _write_report(self, filename: str, html: str) -> str:
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        logger.info('报告已生成: %s', filepath)
        return str(filepath)

    @staticmethod
    def open_report(filepath: str) -> None:
        webbrowser.open(f'file:///{filepath.replace(chr(92), "/")}')

    def get_latest_report(self) -> str | None:
        reports = sorted(self.output_dir.glob('usage_report_*.html'))
        return str(reports[-1]) if reports else None

    @staticmethod
    def _get_current_lang() -> str:
        from .i18n import get_language
        return get_language()
