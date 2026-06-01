/**
 * UsageTracker 网页端设置 - 主逻辑
 * 对应 v0.3.0 路线图 Phase 1-2
 */

const API_BASE = 'http://127.0.0.1:19234';

const API = {
    get: (path) => fetch(`${API_BASE}${path}`).then(r => {
        console.log(`[API GET ${path}] status:`, r.status);
        return r.json();
    }).catch(e => {
        console.error(`[API GET ${path}] error:`, e);
        throw e;
    }),
    post: (path, body) => fetch(`${API_BASE}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    }).then(r => {
        console.log(`[API POST ${path}] status:`, r.status, 'body:', body);
        return r.json();
    }).catch(e => {
        console.error(`[API POST ${path}] error:`, e);
        throw e;
    }),
};

/* ---- Toast ---- */
function toast(msg, duration = 3000) {
    const el = document.getElementById('toast');
    if (!el) return;
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

if (themeBtn) {
    themeBtn.addEventListener('click', () => {
        currentTheme = currentTheme === 'fairy' ? 'geek' : 'fairy';
        applyTheme(currentTheme);
        API.post('/api/config', { web_theme: currentTheme })
            .then(data => console.log('Theme saved:', data))
            .catch(e => console.error('Theme save failed:', e));
    });
}

function applyTheme(theme) {
    const link = document.getElementById('theme-css');
    if (link) link.href = `/static/css/${theme === 'geek' ? 'geek' : 'fairy-tale'}.css`;
    if (themeBtn) themeBtn.textContent = theme === 'geek' ? '🖥️' : '🧚';
}

/* ---- 通用设置 ---- */
async function loadGeneralSettings() {
    console.log('[loadGeneralSettings] fetching...');
    try {
        const data = await API.get('/api/config');
        console.log('[loadGeneralSettings] got:', data);
        if (!data || !data.ok) {
            toast('❌ 加载配置失败: ' + (data ? data.msg : '通信失败'));
            return;
        }
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
    } catch (e) {
        console.error('[loadGeneralSettings] error:', e);
        toast('❌ 加载配置失败: ' + e.message);
    }
}

const btnSaveGeneral = document.getElementById('btn-save-general');
if (btnSaveGeneral) {
    btnSaveGeneral.addEventListener('click', async () => {
        const body = {
            language: document.getElementById('cfg-language').value,
            auto_start: document.getElementById('cfg-auto-start').checked,
            auto_show_daily_report: document.getElementById('cfg-auto-report').checked,
            detection_mode: document.getElementById('cfg-detection-mode').value,
            check_update: document.getElementById('cfg-check-update').checked,
            web_theme: document.getElementById('cfg-web-theme').value,
        };
        console.log('[Save General] body:', body);
        try {
            const data = await API.post('/api/config', body);
            console.log('[Save General] response:', data);
            if (data && data.ok) {
                toast('✅ ' + (data.msg || '设置已保存'));
                applyTheme(body.web_theme);
            } else {
                toast('❌ ' + (data ? data.msg : '保存失败'));
            }
        } catch (e) {
            console.error('[Save General] error:', e);
            toast('❌ 通信失败: ' + e.message);
        }
    });
}

const btnCheckUpdate = document.getElementById('btn-check-update');
if (btnCheckUpdate) {
    btnCheckUpdate.addEventListener('click', async () => {
        try {
            const data = await API.get('/api/check-update');
            if (data && data.ok && data.update) {
                toast(`发现新版本 ${data.update.version}，请前往 GitHub 下载`);
            } else {
                toast('已是最新版本');
            }
        } catch (e) {
            toast('❌ 检查更新失败: ' + e.message);
        }
    });
}

/* ---- 分类管理 ---- */
async function loadCategories() {
    console.log('[loadCategories] fetching...');
    try {
        const data = await API.get('/api/apps');
        console.log('[loadCategories] got:', data);
        if (!data || !data.ok) {
            toast('❌ 加载分类失败');
            return;
        }
        const list = document.getElementById('custom-categories-list');
        if (!list) return;
        list.innerHTML = '';
        const cats = data.custom_categories || [];
        console.log('[loadCategories] categories count:', cats.length);
        if (cats.length === 0) {
            list.innerHTML = '<p style="color:var(--text-secondary);font-size:13px;">暂无自定义分类</p>';
        }
        cats.forEach(cat => {
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
                const r = await API.post('/api/apps', { action: 'remove_category', id: cat.id });
                toast(r && r.ok ? '分类已删除' : '❌ 删除失败');
                loadCategories();
            });
            list.appendChild(div);
        });
        const sel = document.getElementById('category-selector');
        if (sel) {
            const oldVal = sel.value;
            sel.innerHTML = '<option value="">-- 选择分类 --</option>';
            cats.forEach(cat => {
                const opt = document.createElement('option');
                opt.value = cat.id;
                opt.textContent = `${cat.name || cat.id} (${cat.id})`;
                sel.appendChild(opt);
            });
            if (oldVal) {
                sel.value = oldVal;
                if (sel.value) loadCategoryApps(sel.value);
            }
        }
    } catch (e) {
        console.error('[loadCategories] error:', e);
        toast('❌ 加载分类失败: ' + e.message);
    }
}

async function loadCategoryApps(catId) {
    if (!catId) return;
    try {
        const data = await API.get('/api/apps');
        const cat = (data.custom_categories || []).find(c => c.id === catId);
        const list = document.getElementById('category-apps-list');
        if (!list) return;
        list.innerHTML = '';
        if (!cat) return;
        const apps = cat.apps || [];
        if (apps.length === 0) {
            list.innerHTML = '<p style="color:var(--text-secondary);font-size:13px;">该分类暂无应用</p>';
        }
        apps.forEach(appPath => {
            const div = document.createElement('div');
            div.className = 'app-item';
            div.innerHTML = `
                <span class="app-path">${appPath}</span>
                <button class="btn-small" data-app="${appPath}">移除</button>
            `;
            div.querySelector('.btn-small').addEventListener('click', async () => {
                await API.post('/api/apps', { action: 'remove_app', id: catId, exe_path: appPath });
                toast('应用已移除');
                loadCategoryApps(catId);
            });
            list.appendChild(div);
        });
    } catch (e) {
        console.error('[loadCategoryApps] error:', e);
    }
}

const btnAddCategory = document.getElementById('btn-add-category');
if (btnAddCategory) {
    btnAddCategory.addEventListener('click', async () => {
        const id = document.getElementById('new-category-id').value.trim();
        const name = document.getElementById('new-category-name').value.trim();
        if (!id || !name) { toast('请填写分类 ID 和名称'); return; }
        const color = document.getElementById('new-category-color').value || '#0078D4';
        console.log('[Add Category] id:', id, 'name:', name);
        try {
            const data = await API.post('/api/apps', { action: 'add_category', id, name, color });
            console.log('[Add Category] response:', data);
            if (data && data.ok) {
                toast('✅ 分类已添加');
                document.getElementById('new-category-id').value = '';
                document.getElementById('new-category-name').value = '';
                loadCategories();
            } else {
                toast('❌ ' + (data ? data.msg : '添加失败'));
            }
        } catch (e) {
            toast('❌ 通信失败: ' + e.message);
        }
    });
}

const btnAddAppToCategory = document.getElementById('btn-add-app-to-category');
if (btnAddAppToCategory) {
    btnAddAppToCategory.addEventListener('click', async () => {
        const sel = document.getElementById('category-selector');
        const exe = document.getElementById('new-app-path').value.trim();
        if (!sel || !sel.value) { toast('请先选择分类'); return; }
        if (!exe) { toast('请填写应用路径'); return; }
        try {
            const data = await API.post('/api/apps', { action: 'add_app', id: sel.value, exe_path: exe });
            if (data && data.ok) {
                toast('✅ 应用已添加');
                document.getElementById('new-app-path').value = '';
                loadCategoryApps(sel.value);
            } else {
                toast('❌ ' + (data ? data.msg : '添加失败'));
            }
        } catch (e) {
            toast('❌ 通信失败: ' + e.message);
        }
    });
}

/* ---- 忽略名单 ---- */
async function loadIgnoredApps() {
    try {
        const data = await API.get('/api/ignore');
        if (!data || !data.ok) return;
        const list = document.getElementById('ignored-apps-list');
        if (!list) return;
        list.innerHTML = '';
        const apps = data.ignored_apps || [];
        if (apps.length === 0) {
            list.innerHTML = '<p style="color:var(--text-secondary);font-size:13px;">暂无忽略的应用</p>';
        }
        apps.forEach(item => {
            const div = document.createElement('div');
            div.className = 'app-item';
            const exePath = typeof item === 'string' ? item : (item.exe_path || '');
            const appName = typeof item === 'string' ? '' : (item.app_name || '');
            div.innerHTML = `
                <span class="app-path">${exePath} ${appName ? '(' + appName + ')' : ''}</span>
                <button class="btn-small" data-exe="${exePath}">移除</button>
            `;
            div.querySelector('.btn-small').addEventListener('click', async () => {
                await API.post('/api/ignore', { action: 'remove', exe_path: exePath });
                toast('已从忽略名单移除');
                loadIgnoredApps();
            });
            list.appendChild(div);
        });
    } catch (e) {
        console.error('[loadIgnoredApps] error:', e);
    }
}

const btnAddIgnore = document.getElementById('btn-add-ignore');
if (btnAddIgnore) {
    btnAddIgnore.addEventListener('click', async () => {
        const exe = document.getElementById('new-ignore-path').value.trim();
        if (!exe) { toast('请填写应用路径'); return; }
        try {
            const data = await API.post('/api/ignore', { action: 'add', exe_path: exe });
            if (data && data.ok) {
                toast('✅ 已添加到忽略名单');
                document.getElementById('new-ignore-path').value = '';
                loadIgnoredApps();
            } else {
                toast('❌ ' + (data ? data.msg : '添加失败'));
            }
        } catch (e) {
            toast('❌ 通信失败: ' + e.message);
        }
    });
}

/* ---- 游戏目录 ---- */
async function loadGameDirs() {
    try {
        const data = await API.get('/api/games');
        if (!data || !data.ok) return;
        const list = document.getElementById('game-dirs-list');
        if (!list) return;
        list.innerHTML = '';
        const dirs = data.game_dirs || [];
        if (dirs.length === 0) {
            list.innerHTML = '<p style="color:var(--text-secondary);font-size:13px;">暂无游戏目录</p>';
        }
        dirs.forEach(d => {
            const div = document.createElement('div');
            div.className = 'app-item';
            div.innerHTML = `
                <span class="app-path">${d}</span>
                <button class="btn-small" data-dir="${d}">移除</button>
            `;
            div.querySelector('.btn-small').addEventListener('click', async () => {
                await API.post('/api/games', { action: 'remove_dir', dir: d });
                toast('目录已移除');
                loadGameDirs();
            });
            list.appendChild(div);
        });
    } catch (e) {
        console.error('[loadGameDirs] error:', e);
    }
}

const btnAddGameDir = document.getElementById('btn-add-game-dir');
if (btnAddGameDir) {
    btnAddGameDir.addEventListener('click', async () => {
        const d = document.getElementById('new-game-dir').value.trim();
        if (!d) { toast('请填写游戏目录路径'); return; }
        try {
            const data = await API.post('/api/games', { action: 'add_dir', dir: d });
            if (data && data.ok) {
                toast('✅ 游戏目录已添加');
                document.getElementById('new-game-dir').value = '';
                loadGameDirs();
            } else {
                toast('❌ ' + (data ? data.msg : '添加失败'));
            }
        } catch (e) {
            toast('❌ 通信失败: ' + e.message);
        }
    });
}

/* ---- 浏览器规则 ---- */
async function loadBrowserRules() {
    try {
        const data = await API.get('/api/browsers');
        if (!data || !data.ok) return;
        const list = document.getElementById('browser-rules-list');
        if (!list) return;
        list.innerHTML = '';
        const rules = data.browsers || [];
        if (rules.length === 0) {
            list.innerHTML = '<p style="color:var(--text-secondary);font-size:13px;">暂无浏览器规则</p>';
        }
        rules.forEach((rule, idx) => {
            const div = document.createElement('div');
            div.className = 'app-item';
            div.innerHTML = `
                <div>
                    <span class="app-name">${rule.name || '规则' + idx}</span>
                    <span class="app-path">exe: ${rule.exe_path || '*'} | url: ${rule.url_pattern || '*'}</span>
                </div>
                <button class="btn-small" data-idx="${idx}">删除</button>
            `;
            div.querySelector('.btn-small').addEventListener('click', async () => {
                await API.post('/api/browsers', { action: 'remove_rule', index: idx });
                toast('规则已删除');
                loadBrowserRules();
            });
            list.appendChild(div);
        });
    } catch (e) {
        console.error('[loadBrowserRules] error:', e);
    }
}

const btnAddBrowserRule = document.getElementById('btn-add-browser-rule');
if (btnAddBrowserRule) {
    btnAddBrowserRule.addEventListener('click', async () => {
        const name = document.getElementById('new-browser-name').value.trim();
        const exe = document.getElementById('new-browser-exe').value.trim();
        const url = document.getElementById('new-browser-url').value.trim();
        if (!name) { toast('请填写规则名称'); return; }
        try {
            const data = await API.post('/api/browsers', {
                action: 'add_rule',
                rule: { name, exe_path: exe, url_pattern: url }
            });
            if (data && data.ok) {
                toast('✅ 浏览器规则已添加');
                document.getElementById('new-browser-name').value = '';
                document.getElementById('new-browser-exe').value = '';
                document.getElementById('new-browser-url').value = '';
                loadBrowserRules();
            } else {
                toast('❌ ' + (data ? data.msg : '添加失败'));
            }
        } catch (e) {
            toast('❌ 通信失败: ' + e.message);
        }
    });
}

/* ---- 数据库 ---- */
async function loadDatabaseInfo() {
    try {
        const data = await API.get('/api/database');
        if (!data || !data.ok) return;
        const sizeEl = document.getElementById('db-size');
        if (sizeEl) sizeEl.textContent = `${data.db_size_mb || 0} MB`;
        const recEl = document.getElementById('db-records');
        if (recEl) recEl.textContent = `${data.record_count || 0} 条`;
    } catch (e) {
        console.error('[loadDatabaseInfo] error:', e);
    }
}

const btnCleanupDb = document.getElementById('btn-cleanup-db');
if (btnCleanupDb) {
    btnCleanupDb.addEventListener('click', async () => {
        const days = document.getElementById('cleanup-days').value || 90;
        try {
            const data = await API.post('/api/database', { action: 'cleanup', days: parseInt(days) });
            toast(data && data.ok ? `✅ 已清理 ${days} 天前数据` : `❌ ${data ? data.msg : '清理失败'}`);
            loadDatabaseInfo();
        } catch (e) {
            toast('❌ 通信失败: ' + e.message);
        }
    });
}

const btnBackupDb = document.getElementById('btn-backup-db');
if (btnBackupDb) {
    btnBackupDb.addEventListener('click', async () => {
        try {
            const data = await API.post('/api/database', { action: 'backup' });
            toast(data && data.ok ? `✅ 备份成功` : `❌ ${data ? data.msg : '备份失败'}`);
        } catch (e) {
            toast('❌ 通信失败: ' + e.message);
        }
    });
}

/* ---- 反馈 ---- */
async function loadCrashLogs() {
    try {
        const data = await API.get('/api/feedback/logs');
        if (!data || !data.ok) return;
        const list = document.getElementById('crash-logs-list');
        if (!list) return;
        list.innerHTML = '';
        const logs = data.logs || [];
        if (logs.length === 0) {
            list.innerHTML = '<p style="color:var(--text-secondary);font-size:13px;">暂无日志</p>';
        }
        logs.forEach(log => {
            const div = document.createElement('div');
            div.className = 'app-item';
            div.innerHTML = `
                <span class="app-name">${log.name}</span>
                <span class="app-path">${Math.round(log.size / 1024)} KB</span>
            `;
            list.appendChild(div);
        });
    } catch (e) {
        console.error('[loadCrashLogs] error:', e);
    }
}

const btnSubmitFeedback = document.getElementById('btn-submit-feedback');
if (btnSubmitFeedback) {
    btnSubmitFeedback.addEventListener('click', async () => {
        const desc = document.getElementById('feedback-desc').value.trim();
        if (!desc) { toast('请填写问题描述'); return; }
        const contact = document.getElementById('feedback-contact').value.trim();
        try {
            const data = await API.post('/api/feedback', { description: desc, contact });
            if (data && data.ok) {
                toast('✅ 反馈已提交，感谢！');
                document.getElementById('feedback-desc').value = '';
                document.getElementById('feedback-contact').value = '';
            } else {
                toast('❌ ' + (data ? data.msg : '提交失败'));
            }
        } catch (e) {
            toast('❌ 通信失败: ' + e.message);
        }
    });
}

/* ---- 初始化 ---- */
window.addEventListener('DOMContentLoaded', () => {
    console.log('[App] DOMContentLoaded, loading settings...');
    loadGeneralSettings();
});
