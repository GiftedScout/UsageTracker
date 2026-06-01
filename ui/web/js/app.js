/**
 * UsageTracker 网页端设置 - 主逻辑
 * 对应 v0.3.0 路线图 Phase 1-2
 */

const API = {
    get: (path) => fetch(`/api${path}`).then(r => r.json()),
    post: (path, body) => fetch(`/api${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    }).then(r => r.json()),
};

/* ---- Toast ---- */
function toast(msg, duration = 2500) {
    const el = document.getElementById('toast');
    el.textContent = msg;
    el.classList.remove('hidden');
    requestAnimationFrame(() => el.classList.add('show'));
    setTimeout(() => {
        el.classList.remove('show');
        setTimeout(() => el.classList.add('hidden'), 300);
    }, duration);
}

/* ---- Tab 切换 ---- */
document.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', (e) => {
        e.preventDefault();
        const tab = btn.dataset.tab;
        document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
        btn.classList.add('active');
        const tabEl = document.getElementById(`tab-${tab}`);
        if (tabEl) tabEl.classList.add('active');
        if (tab === 'categories') loadCategories();
        if (tab === 'browsers') loadBrowserRules();
        if (tab === 'games') loadGameDirs();
        if (tab === 'ignore') loadIgnoredApps();
        if (tab === 'database') loadDatabaseInfo();
        if (tab === 'feedback') loadCrashLogs();
    });
});

/* ---- 主题切换 ---- */
let currentTheme = 'fairy';
const themeBtn = document.getElementById('btn-theme-switch');

themeBtn.addEventListener('click', () => {
    currentTheme = currentTheme === 'fairy' ? 'geek' : 'fairy';
    applyTheme(currentTheme);
    API.post('/config', { web_theme: currentTheme });
});

function applyTheme(theme) {
    const link = document.getElementById('theme-css');
    link.href = `/static/css/${theme === 'geek' ? 'geek' : 'fairy-tale'}.css`;
    themeBtn.textContent = theme === 'geek' ? '🖥️' : '🌸';
}

/* ---- 通用设置 ---- */
async function loadGeneralSettings() {
    const data = await API.get('/config');
    if (!data.ok) return;
    const langEl = document.getElementById('cfg-language');
    if (langEl) langEl.value = data.language || 'zh-CN';
    const autoStartEl = document.getElementById('cfg-auto-start');
    if (autoStartEl) autoStartEl.checked = !!data.auto_start;
    const autoReportEl = document.getElementById('cfg-auto-report');
    if (autoReportEl) autoReportEl.checked = !!data.auto_show_daily_report;
    const modeEl = document.getElementById('cfg-detection-mode');
    if (modeEl) modeEl.value = data.detection_mode || 'polling';
    const checkUpdateEl = document.getElementById('cfg-check-update');
    if (checkUpdateEl) checkUpdateEl.checked = !!data.check_update;
    const webThemeEl = document.getElementById('cfg-web-theme');
    if (webThemeEl) webThemeEl.value = data.web_theme || 'fairy';
    currentTheme = data.web_theme || 'fairy';
    applyTheme(currentTheme);
    const ver = document.getElementById('app-version');
    if (ver && data.version) ver.textContent = data.version;
}

document.getElementById('btn-save-general').addEventListener('click', async () => {
    const body = {
        language: document.getElementById('cfg-language').value,
        auto_start: document.getElementById('cfg-auto-start').checked,
        auto_show_daily_report: document.getElementById('cfg-auto-report').checked,
        detection_mode: document.getElementById('cfg-detection-mode').value,
        check_update: document.getElementById('cfg-check-update').checked,
        web_theme: document.getElementById('cfg-web-theme').value,
    };
    const data = await API.post('/config', body);
    toast(data.ok ? '✅ 设置已保存' : `❌ ${data.msg}`);
    if (data.ok) applyTheme(body.web_theme);
});

document.getElementById('btn-check-update').addEventListener('click', async () => {
    const data = await API.get('/check-update');
    if (data.ok && data.update) {
        toast(`发现新版本 ${data.update.version}，请前往 GitHub 下载`);
    } else {
        toast('已是最新版本');
    }
});

/* ---- 分类管理 ---- */
async function loadCategories() {
    const data = await API.get('/apps');
    if (!data.ok) return;
    const list = document.getElementById('custom-categories-list');
    if (!list) return;
    list.innerHTML = '';
    (data.custom_categories || []).forEach(cat => {
        const div = document.createElement('div');
        div.className = 'app-item';
        div.innerHTML = `
            <div>
                <span class="app-name">${cat.name || cat.id}</span>
                <span class="app-path" style="color:var(--accent)">${cat.id}</span>
            </div>
            <button class="btn-small" data-id="${cat.id}">删除</button>
        `;
        div.querySelector('.btn-small').addEventListener('click', async () => {
            await API.post('/apps', { action: 'remove_category', id: cat.id });
            toast('分类已删除');
            loadCategories();
        });
        list.appendChild(div);
    });
    const sel = document.getElementById('category-selector');
    if (sel) {
        sel.innerHTML = '';
        (data.custom_categories || []).forEach(cat => {
            const opt = document.createElement('option');
            opt.value = cat.id;
            opt.textContent = `${cat.name || cat.id} (${cat.id})`;
            sel.appendChild(opt);
        });
        if (sel.value) loadCategoryApps(sel.value);
    }
}

async function loadCategoryApps(catId) {
    if (!catId) return;
    const data = await API.get('/apps');
    const cat = (data.custom_categories || []).find(c => c.id === catId);
    const list = document.getElementById('category-apps-list');
    if (!list) return;
    list.innerHTML = '';
    if (!cat) return;
    (cat.apps || []).forEach(exe => {
        const div = document.createElement('div');
        div.className = 'app-item';
        div.innerHTML = `
            <span class="app-path">${exe}</span>
            <button class="btn-small" data-cat="${catId}" data-exe="${exe}">移除</button>
        `;
        div.querySelector('.btn-small').addEventListener('click', async () => {
            await API.post('/apps', { action: 'remove_app', id: catId, exe_path: exe });
            toast('应用已移除');
            loadCategoryApps(catId);
        });
        list.appendChild(div);
    });
}

document.getElementById('category-selector')?.addEventListener('change', (e) => {
    loadCategoryApps(e.target.value);
});

document.getElementById('btn-add-category')?.addEventListener('click', async () => {
    const id = prompt('分类 ID（英文，如 study）：');
    if (!id) return;
    const name = prompt('分类名称（如：学习）：');
    if (!name) return;
    await API.post('/apps', { action: 'add_category', id, name, color: '#0078D4' });
    toast('分类已添加');
    loadCategories();
});

document.getElementById('btn-add-app-to-category')?.addEventListener('click', async () => {
    const catId = document.getElementById('category-selector')?.value;
    if (!catId) { toast('请先选择分类'); return; }
    const exe = prompt('应用 exe 路径：');
    if (!exe) return;
    await API.post('/apps', { action: 'add_app', id: catId, exe_path: exe });
    toast('应用已添加');
    loadCategoryApps(catId);
});

/* ---- 浏览器规则 ---- */
async function loadBrowserRules() {
    const data = await API.get('/browsers');
    const list = document.getElementById('browser-rules-list');
    if (!list) return;
    list.innerHTML = '';
    (data.browsers || []).forEach((rule, idx) => {
        const div = document.createElement('div');
        div.className = 'app-item';
        div.innerHTML = `
            <div>
                <span class="app-name">${rule.browser_exe || '*'}</span>
                <span class="app-path">分类: ${rule.category || 'unknown'}</span>
            </div>
            <button class="btn-small" data-idx="${idx}">删除</button>
        `;
        div.querySelector('.btn-small').addEventListener('click', async () => {
            await API.post('/browsers', { action: 'remove_rule', index: idx });
            toast('规则已删除');
            loadBrowserRules();
        });
        list.appendChild(div);
    });
}

document.getElementById('btn-add-browser-rule')?.addEventListener('click', async () => {
    const browser_exe = prompt('浏览器 exe 名称（如 chrome.exe，留空匹配所有）：');
    const url_pattern = prompt('URL 匹配模式（如 *youtube.com*）：');
    const category = prompt('分类 ID（如 game、study）：');
    if (!category) return;
    await API.post('/browsers', {
        action: 'add_rule',
        rule: { browser_exe: browser_exe || '', url_pattern: url_pattern || '*', category: category || 'other' }
    });
    toast('规则已添加');
    loadBrowserRules();
});

/* ---- 游戏目录 ---- */
async function loadGameDirs() {
    const data = await API.get('/games');
    const list = document.getElementById('game-dirs-list');
    if (!list) return;
    list.innerHTML = '';
    (data.game_dirs || []).forEach(d => {
        const div = document.createElement('div');
        div.className = 'app-item';
        div.innerHTML = `
            <span class="app-path">${d}</span>
            <button class="btn-small" data-dir="${d}">移除</button>
        `;
        div.querySelector('.btn-small').addEventListener('click', async () => {
            await API.post('/games', { action: 'remove_dir', dir: d });
            toast('目录已移除');
            loadGameDirs();
        });
        list.appendChild(div);
    });
}

document.getElementById('btn-add-game-dir')?.addEventListener('click', async () => {
    const d = prompt('游戏目录路径（如 D:\\Games\\Steam）：');
    if (!d) return;
    await API.post('/games', { action: 'add_dir', dir: d });
    toast('目录已添加');
    loadGameDirs();
});

/* ---- 忽略列表 ---- */
async function loadIgnoredApps() {
    const data = await API.get('/ignore');
    const list = document.getElementById('ignored-apps-list');
    if (!list) return;
    list.innerHTML = '';
    (data.ignored_apps || []).forEach(item => {
        const div = document.createElement('div');
        div.className = 'app-item';
        const exe = typeof item === 'string' ? item : (item.exe_path || '');
        const name = typeof item === 'string' ? '' : (item.app_name || '');
        div.innerHTML = `
            <div>
                <span class="app-path">${exe}</span>
                ${name ? `<span class="app-name">${name}</span>` : ''}
            </div>
            <button class="btn-small" data-exe="${exe}">移除</button>
        `;
        div.querySelector('.btn-small').addEventListener('click', async () => {
            await API.post('/ignore', { action: 'remove', exe_path: exe });
            toast('已取消忽略');
            loadIgnoredApps();
        });
        list.appendChild(div);
    });
}

document.getElementById('btn-add-ignore')?.addEventListener('click', async () => {
    const exe = prompt('要忽略的应用 exe 路径：');
    if (!exe) return;
    await API.post('/ignore', { action: 'add', exe_path: exe });
    toast('已添加到忽略列表');
    loadIgnoredApps();
});

/* ---- 数据库 ---- */
async function loadDatabaseInfo() {
    const data = await API.get('/database');
    if (data.ok) {
        const dbSize = document.getElementById('db-size');
        const dbRecords = document.getElementById('db-records');
        if (dbSize) dbSize.textContent = data.db_size_mb ?? '-';
        if (dbRecords) dbRecords.textContent = data.record_count ?? '-';
    }
}

document.getElementById('btn-backup-db')?.addEventListener('click', async () => {
    const data = await API.post('/database', { action: 'backup' });
    toast(data.ok ? `备份成功: ${data.backup_path}` : `备份失败: ${data.msg}`);
});

document.getElementById('btn-cleanup-db')?.addEventListener('click', async () => {
    if (!confirm('确定清理 90 天前的数据？此操作不可恢复。')) return;
    const data = await API.post('/database', { action: 'cleanup', days: 90 });
    toast(data.ok ? '清理完成' : `清理失败: ${data.msg}`);
    loadDatabaseInfo();
});

/* ---- 反馈 ---- */
async function loadCrashLogs() {
    const data = await API.get('/feedback/logs');
    const list = document.getElementById('crash-logs-list');
    if (!list) return;
    list.innerHTML = '';
    (data.logs || []).forEach(log => {
        const div = document.createElement('div');
        div.className = 'app-item';
        div.innerHTML = `
            <span class="app-name">${log.name}</span>
            <span class="app-path">${(log.size / 1024).toFixed(1)} KB</span>
        `;
        list.appendChild(div);
    });
}

document.getElementById('btn-submit-feedback')?.addEventListener('click', async () => {
    const desc = document.getElementById('feedback-desc')?.value?.trim();
    if (!desc) { toast('请填写问题描述'); return; }
    const contact = document.getElementById('feedback-contact')?.value?.trim() || '';
    const data = await API.post('/feedback', { description: desc, contact });
    if (data.ok) {
        toast('反馈已提交，感谢！');
        const descEl = document.getElementById('feedback-desc');
        const contactEl = document.getElementById('feedback-contact');
        if (descEl) descEl.value = '';
        if (contactEl) contactEl.value = '';
    } else {
        toast(`提交失败: ${data.msg}`);
    }
});

/* ---- 初始化 ---- */
document.addEventListener('DOMContentLoaded', () => {
    loadGeneralSettings();
});
