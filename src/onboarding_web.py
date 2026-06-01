"""
首次运行引导页面 - 网页端（替代 tkinter onboarding）
供 Bridge HTTP 服务 /onboarding 端点返回
"""

def render_onboarding_page(theme: str = 'fairy') -> str:
    """渲染引导页面 HTML，theme: 'fairy' | 'geek'"""
    css_file = 'fairy-tale' if theme == 'fairy' else 'geek'
    if theme == 'fairy':
        bg = 'background: linear-gradient(135deg, #FFF8E7 0%, #F0F7FF 50%, #F5F0FF 100%); color: #2C3E50;'
        accent = '#5B8C5A'
        card_bg = 'rgba(255,255,255,0.85)'
        btn_hover = '#4A7A4A'
        step_bg = 'rgba(91,140,90,0.08)'
    else:
        bg = 'background: linear-gradient(135deg, #0a0f1a 0%, #141b2d 100%); color: #E0E6ED;'
        accent = '#1E90FF'
        card_bg = 'rgba(26,35,50,0.85)'
        btn_hover = '#1AB2FF'
        step_bg = 'rgba(30,144,255,0.08)'

    js = """
<script>
let currentTheme = '""" + theme + """';

function selectTheme(t) {
    currentTheme = t;
    document.getElementById('theme-fairy').classList.toggle('active', t === 'fairy');
    document.getElementById('theme-geek').classList.toggle('active', t === 'geek');
}

async function finishOnboarding() {
    const autoStart = document.getElementById('opt-autostart').checked;
    const body = {
        auto_start: autoStart,
        web_theme: currentTheme,
        first_run: false,
        privacy_accepted: true,
    };
    try {
        const resp = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        const data = await resp.json();
        if (data.ok) {
            window.location.href = '/settings';
        } else {
            alert('保存失败: ' + (data.msg || '未知错误'));
        }
    } catch(e) {
        alert('通信失败: ' + e.message);
    }
}
</script>"""

    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>UsageTracker - 欢迎</title>
<link rel="stylesheet" href="/static/css/""" + css_file + """.css">
<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
        """ + bg + """
        font-family: 'Segoe UI', system-ui, sans-serif;
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .card {
        background: """ + card_bg + """;
        backdrop-filter: blur(12px);
        border-radius: 20px;
        padding: 40px 48px;
        max-width: 520px;
        width: 90%;
        box-shadow: 0 8px 32px rgba(0,0,0,0.18);
        text-align: center;
    }
    .logo { font-size: 48px; margin-bottom: 8px; }
    h1 { font-size: 22px; margin-bottom: 6px; }
    .subtitle { font-size: 13px; opacity: 0.6; margin-bottom: 28px; }
    .step { text-align: left; margin: 16px 0; padding: 14px 16px; border-radius: 10px;
             background: """ + step_bg + """; }
    .step-title { font-weight: 600; font-size: 14px; margin-bottom: 4px; }
    .step-desc { font-size: 12px; opacity: 0.7; line-height: 1.5; }
    .toggle-row { display: flex; align-items: center; justify-content: space-between;
                   margin: 20px 0; padding: 12px 16px; border-radius: 10px;
                   background: """ + step_bg + """; }
    .toggle-label { font-size: 14px; font-weight: 500; }
    .toggle-sub { font-size: 11px; opacity: 0.6; }
    .toggle-switch {
        position: relative; width: 44px; height: 24px; cursor: pointer;
    }
    .toggle-switch input { display: none; }
    .toggle-slider {
        position: absolute; inset: 0; border-radius: 12px;
        background: #ccc; transition: 0.3s;
    }
    .toggle-slider::before {
        content: ''; position: absolute; width: 18px; height: 18px;
        left: 3px; top: 3px; border-radius: 50%;
        background: white; transition: 0.3s;
    }
    .toggle-switch input:checked + .toggle-slider {
        background: """ + accent + """;
    }
    .toggle-switch input:checked + .toggle-slider::before {
        transform: translateX(20px);
    }
    .theme-row { display: flex; gap: 10px; margin: 16px 0; justify-content: center; }
    .theme-btn {
        flex: 1; padding: 10px; border-radius: 10px; border: 2px solid transparent;
        cursor: pointer; font-size: 13px; transition: 0.2s;
        background: """ + step_bg + """;
    }
    .theme-btn.active { border-color: """ + accent + """; }
    .theme-btn:hover { opacity: 0.85; }
    .btn-primary {
        margin-top: 24px; width: 100%; padding: 12px;
        background: """ + accent + """; color: white; border: none;
        border-radius: 10px; font-size: 15px; cursor: pointer; transition: 0.2s;
    }
    .btn-primary:hover { background: """ + btn_hover + """; }
    .hint { font-size: 11px; opacity: 0.5; margin-top: 12px; }
</style>
</head>
<body>
<div class="card">
    <div class="logo">&#128218;</div>
    <h1>欢迎使用 UsageTracker</h1>
    <p class="subtitle">v0.3.0 &nbsp;&middot;&nbsp; 网页端设置已就绪</p>

    <div class="step">
        <div class="step-title">&#9312; 开机自启（强烈建议）</div>
        <div class="step-desc">勾选后 UsageTracker 会在开机时自动启动并开始追踪。</div>
        <div class="toggle-row">
            <div>
                <div class="toggle-label">启用开机自启</div>
                <div class="toggle-sub">关闭后需手动启动</div>
            </div>
            <label class="toggle-switch">
                <input type="checkbox" id="opt-autostart" checked>
                <span class="toggle-slider"></span>
            </label>
        </div>
    </div>

    <div class="step">
        <div class="step-title">&#9313; 选择网页端主题</div>
        <div class="step-desc">设置页面将使用你选择的主题风格。</div>
        <div class="theme-row">
            <div class="theme-btn active" id="theme-fairy" onclick="selectTheme('fairy')">&#127800; 童话</div>
            <div class="theme-btn" id="theme-geek" onclick="selectTheme('geek')">&#128421;&#65039; 极客</div>
        </div>
    </div>

    <div class="step">
        <div class="step-title">&#9314; 完成引导</div>
        <div class="step-desc">点击完成后将保存设置，并打开设置页面。</div>
    </div>

    <button class="btn-primary" onclick="finishOnboarding()">完成，进入设置 &rarr;</button>
    <p class="hint">设置页面可随时从系统托盘右键菜单打开</p>
</div>
""" + js + """
</body>
</html>"""
    return html


if __name__ == '__main__':
    print(render_onboarding_page('fairy'))
