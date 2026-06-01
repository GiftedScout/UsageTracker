/**
 * UsageTracker Web Settings - Main Logic
 * v0.3.0: i18n, validation, process picker, auto-detect display
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

/* ---- i18n ---- */
const I18N = {
    'zh-CN': {
        'nav.general': '通用', 'nav.categories': '分类', 'nav.browsers': '浏览器',
        'nav.games': '游戏', 'nav.ignore': '忽略', 'nav.database': '数据库', 'nav.feedback': '反馈',
        'general.title': '通用设置', 'general.language': '语言', 'general.auto_start': '开机自启动',
        'general.auto_report': '自动显示昨日报告', 'general.detection_mode': '检测模式',
        'general.check_update': '自动检查更新', 'general.web_theme': '网页主题',
        'general.save': '保存设置', 'general.about': '关于', 'general.license': '许可：GPL-3.0',
        'general.check_update_btn': '检查更新', 'general.polling': '轮询模式',
        'general.event': '事件驱动',
        'general.tray_hint': 'UsageTracker 正在系统托盘中运行，关闭此页面不会退出程序。',
        'categories.title': '应用分类', 'categories.custom': '自定义分类',
        'categories.no_categories': '暂无自定义分类', 'categories.apps_in': '分类中的应用',
        'categories.no_apps': '该分类暂无应用', 'categories.select': '选择分类',
        'categories.id_placeholder': '分类 ID（如 dev）',
        'categories.name_placeholder': '分类名称（如 开发工具）',
        'categories.app_placeholder': '应用路径（如 C:\\app\\code.exe）',
        'browsers.title': '浏览器规则', 'browsers.desc': '配置浏览器 URL 匹配规则（自动检测的浏览器无需手动添加）',
        'browsers.no_rules': '暂无浏览器规则', 'browsers.name': '规则名称',
        'browsers.exe': '浏览器可执行文件路径', 'browsers.url': 'URL 匹配模式',
        'browsers.name_placeholder': '如 GitHub',
        'browsers.exe_placeholder': '如 C:\\app\\chrome.exe（留空匹配所有）',
        'browsers.url_placeholder': '如 github.com（留空匹配所有）',
        'browsers.add_rule': '添加规则', 'browsers.auto_label': '已自动检测到以下浏览器：',
        'games.title': '游戏目录', 'games.desc': '配置游戏可执行文件所在目录（Steam 游戏自动扫描无需手动添加）',
        'games.no_dirs': '暂无游戏目录',
        'games.dir_placeholder': '游戏目录路径（如 D:\\Steam\\steamapps\\common）',
        'games.auto_label': '已自动扫描到以下游戏：',
        'ignore.title': '忽略列表', 'ignore.desc': '被忽略的应用不会计入使用时长',
        'ignore.no_apps': '暂无忽略的应用',
        'ignore.path_placeholder': '应用路径（如 C:\\Windows\\System32\\cmd.exe）',
        'database.title': '数据库管理', 'database.size': '数据库大小',
        'database.records': '记录条数', 'database.cleanup_label': '清理天数：',
        'database.days': '天', 'database.backup': '备份数据库', 'database.cleanup': '清理旧数据',
        'database.preview': '数据预览', 'database.no_data': '暂无数据',
        'feedback.title': '问题反馈', 'feedback.desc_label': '问题描述',
        'feedback.desc_placeholder': '描述你遇到的问题...',
        'feedback.contact_label': '联系方式（可选）',
        'feedback.contact_placeholder': '邮箱或微信',
        'feedback.submit': '提交反馈', 'feedback.logs_title': '崩溃日志',
        'feedback.no_logs': '暂无日志', 'feedback.logs_hint': '点击日志文件查看内容',
        'feedback.open_folder': '打开反馈文件夹',
        'process_picker.title': '选择进程', 'process_picker.search': '搜索进程...',
        'process_picker.close': '取消',
        'btn.add': '添加', 'btn.remove': '删除', 'btn.from_process': '从进程选择',
        'cat.browser': '浏览器', 'cat.game': '游戏', 'cat.dev': '开发工具',
        'cat.communication': '通讯工具', 'cat.entertainment': '影音娱乐',
        'toast.saved': '设置已保存', 'toast.added': '已添加',
        'toast.removed': '已移除', 'toast.empty': '请填写内容',
        'toast.invalid_id': '分类 ID 只能包含字母、数字、下划线和连字符',
        'toast.already_exists': '已存在',
        'toast.no_selection': '请先选择分类',
        'toast.up_to_date': '已是最新版本',
        'toast.new_version': '发现新版本',
        'fairy_theme': '🌸 童话', 'geek_theme': '🖥️ 极客',
    },
    'en': {
        'nav.general': 'General', 'nav.categories': 'Categories', 'nav.browsers': 'Browsers',
        'nav.games': 'Games', 'nav.ignore': 'Ignore', 'nav.database': 'Database', 'nav.feedback': 'Feedback',
        'general.title': 'General Settings', 'general.language': 'Language',
        'general.auto_start': 'Auto Start', 'general.auto_report': 'Auto Show Daily Report',
        'general.detection_mode': 'Detection Mode', 'general.check_update': 'Auto Check Updates',
        'general.web_theme': 'Web Theme', 'general.save': 'Save Settings',
        'general.about': 'About', 'general.license': 'License: GPL-3.0',
        'general.check_update_btn': 'Check for Updates', 'general.polling': 'Polling',
        'general.event': 'Event-driven',
        'general.tray_hint': 'UsageTracker is running in the system tray. Closing this page will not exit the program.',
        'categories.title': 'App Categories', 'categories.custom': 'Custom Categories',
        'categories.no_categories': 'No custom categories', 'categories.apps_in': 'Apps in Category',
        'categories.no_apps': 'No apps in this category', 'categories.select': 'Select category',
        'categories.id_placeholder': 'Category ID (e.g. dev)',
        'categories.name_placeholder': 'Category Name (e.g. Dev Tools)',
        'categories.app_placeholder': 'App path (e.g. C:\\app\\code.exe)',
        'browsers.title': 'Browser Rules',
        'browsers.desc': 'Configure browser URL matching rules (auto-detected browsers need no manual setup)',
        'browsers.no_rules': 'No browser rules', 'browsers.name': 'Rule Name',
        'browsers.exe': 'Browser Executable Path', 'browsers.url': 'URL Pattern',
        'browsers.name_placeholder': 'e.g. GitHub',
        'browsers.exe_placeholder': 'e.g. C:\\app\\chrome.exe (leave empty for all)',
        'browsers.url_placeholder': 'e.g. github.com (leave empty for all)',
        'browsers.add_rule': 'Add Rule', 'browsers.auto_label': 'Auto-detected browsers:',
        'games.title': 'Game Directories',
        'games.desc': 'Configure game executable directories (Steam games are auto-scanned)',
        'games.no_dirs': 'No game directories',
        'games.dir_placeholder': 'Game directory (e.g. D:\\Steam\\steamapps\\common)',
        'games.auto_label': 'Auto-scanned games:',
        'ignore.title': 'Ignore List',
        'ignore.desc': 'Ignored apps will not be counted in usage time',
        'ignore.no_apps': 'No ignored apps',
        'ignore.path_placeholder': 'App path (e.g. C:\\Windows\\System32\\cmd.exe)',
        'database.title': 'Database Management', 'database.size': 'Database Size',
        'database.records': 'Records', 'database.cleanup_label': 'Cleanup days: ',
        'database.days': 'days', 'database.backup': 'Backup Database',
        'database.cleanup': 'Cleanup Old Data',
        'database.preview': 'Data Preview', 'database.no_data': 'No data',
        'feedback.title': 'Feedback', 'feedback.desc_label': 'Description',
        'feedback.desc_placeholder': 'Describe the issue...',
        'feedback.contact_label': 'Contact (optional)',
        'feedback.contact_placeholder': 'Email or WeChat',
        'feedback.submit': 'Submit Feedback', 'feedback.logs_title': 'Crash Logs',
        'feedback.no_logs': 'No logs', 'feedback.logs_hint': 'Click a log file to view its content',
        'feedback.open_folder': 'Open feedback folder',
        'process_picker.title': 'Select Process',
        'process_picker.search': 'Search process name...',
        'process_picker.close': 'Cancel',
        'btn.add': 'Add', 'btn.remove': 'Remove', 'btn.from_process': 'From process',
        'cat.browser': 'Browser', 'cat.game': 'Game', 'cat.dev': 'Dev Tools',
        'cat.communication': 'Communication', 'cat.entertainment': 'Entertainment',
        'toast.saved': 'Settings saved', 'toast.added': 'Added',
        'toast.removed': 'Removed', 'toast.empty': 'Please fill in the field',
        'toast.invalid_id': 'Category ID can only contain letters, numbers, underscores and hyphens',
        'toast.already_exists': 'Already exists',
        'toast.no_selection': 'Please select a category first',
        'toast.up_to_date': 'Up to date', 'toast.new_version': 'New version available',
        'fairy_theme': '🌸 Fairy', 'geek_theme': '🖥️ Geek',
    },
};

let currentLang = 'zh-CN';

function t(key) {
    return (I18N[currentLang] && I18N[currentLang][key]) || key;
}

function translateCatName(cat) {
    const builtin = { browser: 'cat.browser', game: 'cat.game', dev: 'cat.dev',
                      communication: 'cat.communication', entertainment: 'cat.entertainment' };
    if (cat.id && builtin[cat.id]) return t(builtin[cat.id]);
    return cat.name || cat.id;
}

function applyLanguage(lang) {
    currentLang = lang;
    document.documentElement.lang = lang === 'zh-CN' ? 'zh-CN' : 'en';
    // Update text content
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        const val = t(key);
        if (val && val !== key) el.textContent = val;
    });
    // Update placeholders
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        const val = t(key);
        if (val && val !== key) el.placeholder = val;
    });
    // Update select options with data-i18n-opt
    document.querySelectorAll('[data-i18n-opt]').forEach(el => {
        const key = el.getAttribute('data-i18n-opt');
        const val = t(key);
        if (val && val !== key) el.textContent = val;
    });
    // Refresh current tab content
    const activeTab = document.querySelector('.nav-item.active');
    if (activeTab) {
        const tab = activeTab.dataset.tab;
        if (tab === 'categories') loadCategories();
        else if (tab === 'browsers') loadBrowserRules();
        else if (tab === 'games') loadGameDirs();
        else if (tab === 'ignore') loadIgnoredApps();
    }
}

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

/* ---- Tab Switch ---- */
document.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', (e) => {
        e.preventDefault();
        const tab = btn.dataset.tab;
        document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
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

/* ---- Theme Switch ---- */
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
    if (themeBtn) themeBtn.textContent = theme === 'geek' ? '🖥️' : '🌸';
}

/* ---- Validation ---- */
function validateCategoryId(id) {
    return /^[a-zA-Z0-9_-]+$/.test(id);
}

/* ---- Process Picker ---- */
let _processCache = null;
let _pickerCallback = null;

async function fetchProcesses() {
    if (_processCache) return _processCache;
    try {
        const data = await API.get('/api/processes');
        if (data && data.ok) {
            _processCache = data.processes || [];
        }
    } catch (e) {
        console.error('Failed to fetch processes:', e);
        _processCache = [];
    }
    return _processCache || [];
}

function openProcessPicker(callback) {
    _pickerCallback = callback;
    const modal = document.getElementById('process-modal');
    const search = document.getElementById('process-search');
    const list = document.getElementById('process-list');
    modal.classList.add('show');
    search.value = '';
    search.focus();

    fetchProcesses().then(processes => {
        renderProcessList(processes, '');
    });
}

function renderProcessList(processes, filter) {
    const list = document.getElementById('process-list');
    const fl = filter.toLowerCase();
    const filtered = fl ? processes.filter(p =>
        p.name.toLowerCase().includes(fl) || p.exe_path.toLowerCase().includes(fl)
    ) : processes;
    list.innerHTML = '';
    if (filtered.length === 0) {
        list.innerHTML = `<p style="padding:12px;color:var(--text-secondary);font-size:13px;">No processes found</p>`;
        return;
    }
    const frag = document.createDocumentFragment();
    const limit = Math.min(filtered.length, 100);
    for (let i = 0; i < limit; i++) {
        const p = filtered[i];
        const div = document.createElement('div');
        div.className = 'modal-item';
        div.innerHTML = `<span class="proc-name">${p.name}</span><span class="proc-path">${p.exe_path}</span>`;
        div.addEventListener('click', () => {
            document.getElementById('process-modal').classList.remove('show');
            if (_pickerCallback) _pickerCallback(p.exe_path, p.name);
            _pickerCallback = null;
        });
        frag.appendChild(div);
    }
    list.appendChild(frag);
}

document.getElementById('process-modal-close').addEventListener('click', () => {
    document.getElementById('process-modal').classList.remove('show');
    _pickerCallback = null;
});
document.getElementById('process-modal').addEventListener('click', (e) => {
    if (e.target.id === 'process-modal') {
        document.getElementById('process-modal').classList.remove('show');
        _pickerCallback = null;
    }
});
document.getElementById('process-search').addEventListener('input', (e) => {
    fetchProcesses().then(processes => renderProcessList(processes, e.target.value));
});

// Process picker buttons
document.getElementById('btn-pick-process-category').addEventListener('click', () => {
    openProcessPicker((exePath) => {
        document.getElementById('new-app-path').value = exePath;
    });
});
document.getElementById('btn-pick-process-ignore').addEventListener('click', () => {
    openProcessPicker((exePath) => {
        document.getElementById('new-ignore-path').value = exePath;
    });
});

/* ---- Populate datalist for autocomplete ---- */
async function populateDatalist(datalistId) {
    const dl = document.getElementById(datalistId);
    if (!dl) return;
    const processes = await fetchProcesses();
    dl.innerHTML = '';
    const frag = document.createDocumentFragment();
    for (const p of processes) {
        if (p.exe_path && p.exe_path !== p.name) {
            const opt = document.createElement('option');
            opt.value = p.exe_path;
            opt.label = p.name;
            frag.appendChild(opt);
        }
    }
    dl.appendChild(frag);
}

/* ---- General Settings ---- */
async function loadGeneralSettings() {
    console.log('[loadGeneralSettings] fetching...');
    try {
        const data = await API.get('/api/config');
        console.log('[loadGeneralSettings] got:', data);
        if (!data || !data.ok) {
            toast('Failed to load config: ' + (data ? data.msg : 'Connection failed'));
            return;
        }
        const lang = data.language || 'zh-CN';
        currentLang = lang;
        applyLanguage(lang);

        const langEl = document.getElementById('cfg-language');
        if (langEl) langEl.value = lang;
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

        // Pre-populate process datalist
        populateDatalist('process-datalist');
        populateDatalist('process-datalist-ignore');
    } catch (e) {
        console.error('[loadGeneralSettings] error:', e);
        toast('Failed to load config: ' + e.message);
    }
}

const btnSaveGeneral = document.getElementById('btn-save-general');
if (btnSaveGeneral) {
    btnSaveGeneral.addEventListener('click', async () => {
        const newLang = document.getElementById('cfg-language').value;
        const body = {
            language: newLang,
            auto_start: document.getElementById('cfg-auto-start').checked,
            auto_show_daily_report: document.getElementById('cfg-auto-report').checked,
            check_update: document.getElementById('cfg-check-update').checked,
            web_theme: document.getElementById('cfg-web-theme').value,
        };
        console.log('[Save General] body:', body);
        try {
            const data = await API.post('/api/config', body);
            console.log('[Save General] response:', data);
            if (data && data.ok) {
                toast('✅ ' + (data.msg || t('toast.saved')));
                // Apply language change immediately
                if (newLang !== currentLang) {
                    applyLanguage(newLang);
                }
                applyTheme(body.web_theme);
                // detection_mode always forced to polling
                const modeEl = document.getElementById('cfg-detection-mode');
                if (modeEl) modeEl.value = 'polling';
            } else {
                toast('❌ ' + (data ? data.msg : 'Save failed'));
            }
        } catch (e) {
            console.error('[Save General] error:', e);
            toast('❌ Connection failed: ' + e.message);
        }
    });
}

const btnCheckUpdate = document.getElementById('btn-check-update');
if (btnCheckUpdate) {
    btnCheckUpdate.addEventListener('click', async () => {
        try {
            const data = await API.get('/api/check-update');
            if (data && data.ok && data.update) {
                toast(`${t('toast.new_version')} ${data.update.version}`);
            } else {
                toast('✅ ' + t('toast.up_to_date'));
            }
        } catch (e) {
            toast('❌ Check update failed: ' + e.message);
        }
    });
}

/* ---- Categories ---- */
async function loadCategories() {
    try {
        const data = await API.get('/api/apps');
        if (!data || !data.ok) return;
        const list = document.getElementById('custom-categories-list');
        if (!list) return;
        list.innerHTML = '';
        const cats = data.custom_categories || [];
        if (cats.length === 0) {
            list.innerHTML = `<p style="color:var(--text-secondary);font-size:13px;">${t('categories.no_categories')}</p>`;
        }
        cats.forEach(cat => {
            const displayName = translateCatName(cat);
            const div = document.createElement('div');
            div.className = 'app-item';
            div.innerHTML = `
                <div style="display:flex;align-items:center;gap:8px;">
                    <span style="display:inline-block;width:12px;height:12px;border-radius:3px;background:${cat.color || '#0078D4'};"></span>
                    <span class="app-name">${displayName}</span>
                </div>
                <button class="btn-small" data-id="${cat.id}">${t('btn.remove')}</button>
            `;
            div.querySelector('.btn-small').addEventListener('click', async () => {
                const r = await API.post('/api/apps', { action: 'remove_category', id: cat.id });
                toast(r && r.ok ? t('toast.removed') : '❌ ' + (r ? r.msg : 'Failed'));
                loadCategories();
            });
            list.appendChild(div);
        });
        const sel = document.getElementById('category-selector');
        if (sel) {
            const oldVal = sel.value;
            sel.innerHTML = `<option value="">-- ${t('categories.select')} --</option>`;
            cats.forEach(cat => {
                const opt = document.createElement('option');
                opt.value = cat.id;
                opt.textContent = translateCatName(cat);
                sel.appendChild(opt);
            });
            if (oldVal) {
                sel.value = oldVal;
                if (sel.value) loadCategoryApps(sel.value);
            }
        }
    } catch (e) {
        console.error('[loadCategories] error:', e);
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
            list.innerHTML = `<p style="color:var(--text-secondary);font-size:13px;">${t('categories.no_apps')}</p>`;
        }
        apps.forEach(appPath => {
            const div = document.createElement('div');
            div.className = 'app-item';
            div.innerHTML = `
                <span class="app-path">${appPath}</span>
                <button class="btn-small" data-app="${appPath}">${t('btn.remove')}</button>
            `;
            div.querySelector('.btn-small').addEventListener('click', async () => {
                await API.post('/api/apps', { action: 'remove_app', id: catId, exe_path: appPath });
                toast(t('toast.removed'));
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
        if (!id || !name) { toast(t('toast.empty')); return; }
        if (!validateCategoryId(id)) { toast(t('toast.invalid_id')); return; }
        const color = document.getElementById('new-category-color').value || '#0078D4';
        try {
            const data = await API.post('/api/apps', { action: 'add_category', id, name, color });
            if (data && data.ok) {
                toast('✅ ' + t('toast.added'));
                document.getElementById('new-category-id').value = '';
                document.getElementById('new-category-name').value = '';
                loadCategories();
            } else {
                toast('❌ ' + (data ? data.msg : 'Failed'));
            }
        } catch (e) {
            toast('❌ ' + e.message);
        }
    });
}

// 分类选择器 change 事件：切换分类时刷新应用列表
const categorySelector = document.getElementById('category-selector');
if (categorySelector) {
    categorySelector.addEventListener('change', () => {
        if (categorySelector.value) {
            loadCategoryApps(categorySelector.value);
        } else {
            const list = document.getElementById('category-apps-list');
            if (list) list.innerHTML = `<p style="color:var(--text-secondary);font-size:13px;">${t('categories.no_apps')}</p>`;
        }
    });
}

const btnAddAppToCategory = document.getElementById('btn-add-app-to-category');
if (btnAddAppToCategory) {
    btnAddAppToCategory.addEventListener('click', async () => {
        const sel = document.getElementById('category-selector');
        const exe = document.getElementById('new-app-path').value.trim();
        if (!sel || !sel.value) { toast(t('toast.no_selection')); return; }
        if (!exe) { toast(t('toast.empty')); return; }
        try {
            const data = await API.post('/api/apps', { action: 'add_app', id: sel.value, exe_path: exe });
            if (data && data.ok) {
                toast('✅ ' + t('toast.added'));
                document.getElementById('new-app-path').value = '';
                loadCategoryApps(sel.value);
            } else {
                toast('❌ ' + (data ? data.msg : 'Failed'));
            }
        } catch (e) {
            toast('❌ ' + e.message);
        }
    });
}

/* ---- Ignore ---- */
async function loadIgnoredApps() {
    try {
        const data = await API.get('/api/ignore');
        if (!data || !data.ok) return;
        const list = document.getElementById('ignored-apps-list');
        if (!list) return;
        list.innerHTML = '';
        const apps = data.ignored_apps || [];
        if (apps.length === 0) {
            list.innerHTML = `<p style="color:var(--text-secondary);font-size:13px;">${t('ignore.no_apps')}</p>`;
        }
        apps.forEach(item => {
            const div = document.createElement('div');
            div.className = 'app-item';
            const exePath = typeof item === 'string' ? item : (item.exe_path || '');
            const appName = typeof item === 'string' ? '' : (item.app_name || '');
            div.innerHTML = `
                <span class="app-path">${exePath} ${appName ? '(' + appName + ')' : ''}</span>
                <button class="btn-small" data-exe="${exePath}">${t('btn.remove')}</button>
            `;
            div.querySelector('.btn-small').addEventListener('click', async () => {
                await API.post('/api/ignore', { action: 'remove', exe_path: exePath });
                toast(t('toast.removed'));
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
        if (!exe) { toast(t('toast.empty')); return; }
        try {
            const data = await API.post('/api/ignore', { action: 'add', exe_path: exe });
            if (data && data.ok) {
                toast('✅ ' + t('toast.added'));
                document.getElementById('new-ignore-path').value = '';
                loadIgnoredApps();
            } else {
                toast('❌ ' + (data ? data.msg : 'Failed'));
            }
        } catch (e) {
            toast('❌ ' + e.message);
        }
    });
}

/* ---- Game Dirs ---- */
async function loadGameDirs() {
    try {
        const data = await API.get('/api/games');
        if (!data || !data.ok) return;
        const list = document.getElementById('game-dirs-list');
        if (!list) return;
        list.innerHTML = '';
        const dirs = data.game_dirs || [];
        if (dirs.length === 0) {
            list.innerHTML = `<p style="color:var(--text-secondary);font-size:13px;">${t('games.no_dirs')}</p>`;
        }
        dirs.forEach(d => {
            const div = document.createElement('div');
            div.className = 'app-item';
            div.innerHTML = `
                <span class="app-path">${d}</span>
                <button class="btn-small" data-dir="${d}">${t('btn.remove')}</button>
            `;
            div.querySelector('.btn-small').addEventListener('click', async () => {
                await API.post('/api/games', { action: 'remove_dir', dir: d });
                toast(t('toast.removed'));
                loadGameDirs();
            });
            list.appendChild(div);
        });
        // Show auto-detected games (from classifier, not steamapps path filter)
        const detectedEl = document.getElementById('detected-games');
        if (detectedEl) {
            try {
                const classData = await API.get('/api/classifier-games');
                if (classData && classData.ok && classData.games && classData.games.length > 0) {
                    detectedEl.innerHTML = `<strong>${t('games.auto_label')}</strong><br>` +
                        classData.games.map(g => `${g.name} (${g.exe})`).join(', ');
                    detectedEl.style.display = 'block';
                } else {
                    detectedEl.style.display = 'none';
                }
            } catch (e) { /* silent */ }
        }
    } catch (e) {
        console.error('[loadGameDirs] error:', e);
    }
}

const btnAddGameDir = document.getElementById('btn-add-game-dir');
if (btnAddGameDir) {
    btnAddGameDir.addEventListener('click', async () => {
        const d = document.getElementById('new-game-dir').value.trim();
        if (!d) { toast(t('toast.empty')); return; }
        try {
            const data = await API.post('/api/games', { action: 'add_dir', dir: d });
            if (data && data.ok) {
                toast('✅ ' + t('toast.added'));
                document.getElementById('new-game-dir').value = '';
                loadGameDirs();
            } else {
                toast('❌ ' + (data ? data.msg : 'Failed'));
            }
        } catch (e) {
            toast('❌ ' + e.message);
        }
    });
}

/* ---- Browser Rules ---- */
async function loadBrowserRules() {
    try {
        const data = await API.get('/api/browsers');
        if (!data || !data.ok) return;
        const list = document.getElementById('browser-rules-list');
        if (!list) return;
        list.innerHTML = '';
        const rules = data.browsers || [];
        if (rules.length === 0) {
            list.innerHTML = `<p style="color:var(--text-secondary);font-size:13px;">${t('browsers.no_rules')}</p>`;
        }
        rules.forEach((rule, idx) => {
            const div = document.createElement('div');
            div.className = 'app-item';
            div.innerHTML = `
                <div>
                    <span class="app-name">${rule.name || 'Rule ' + idx}</span>
                    <span class="app-path">exe: ${rule.exe_path || '*'} | url: ${rule.url_pattern || '*'}</span>
                </div>
                <button class="btn-small" data-idx="${idx}">删除</button>
            `;
            div.querySelector('.btn-small').addEventListener('click', async () => {
                await API.post('/api/browsers', { action: 'remove_rule', index: idx });
                toast(t('toast.removed'));
                loadBrowserRules();
            });
            list.appendChild(div);
        });
        // Show auto-detected browsers
        const detectedEl = document.getElementById('detected-browsers');
        if (detectedEl) {
            try {
                const procData = await API.get('/api/processes');
                if (procData && procData.ok) {
                    const browserNames = ['msedge.exe', 'chrome.exe', 'firefox.exe',
                        'brave.exe', 'opera.exe', 'vivaldi.exe', 'arc.exe'];
                    const detected = procData.processes.filter(p =>
                        browserNames.includes(p.name.toLowerCase())
                    );
                    if (detected.length > 0) {
                        detectedEl.innerHTML = `<strong>${t('browsers.auto_label')}</strong><br>` +
                            detected.map(p => p.name).join(', ');
                        detectedEl.style.display = 'block';
                    } else {
                        detectedEl.style.display = 'none';
                    }
                }
            } catch (e) { /* silent */ }
        }
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
        if (!name) { toast(t('toast.empty')); return; }
        try {
            const data = await API.post('/api/browsers', {
                action: 'add_rule',
                rule: { name, exe_path: exe, url_pattern: url }
            });
            if (data && data.ok) {
                toast('✅ ' + t('toast.added'));
                document.getElementById('new-browser-name').value = '';
                document.getElementById('new-browser-exe').value = '';
                document.getElementById('new-browser-url').value = '';
                loadBrowserRules();
            } else {
                toast('❌ ' + (data ? data.msg : 'Failed'));
            }
        } catch (e) {
            toast('❌ ' + e.message);
        }
    });
}

/* ---- Database ---- */
async function loadDatabaseInfo() {
    try {
        const data = await API.get('/api/database');
        if (!data || !data.ok) return;
        const sizeEl = document.getElementById('db-size');
        if (sizeEl) sizeEl.textContent = `${data.db_size_mb || 0} MB`;
        const recEl = document.getElementById('db-records');
        if (recEl) recEl.textContent = `${data.record_count || 0}`;
    } catch (e) {
        console.error('[loadDatabaseInfo] error:', e);
    }
    // Load preview
    try {
        const preview = await API.get('/api/database/preview');
        if (!preview || !preview.ok) return;
        const tableEl = document.getElementById('db-preview-table');
        if (!tableEl) return;
        const records = preview.records || [];
        if (records.length === 0) {
            tableEl.innerHTML = `<p style="color:var(--text-secondary);font-size:13px;">${t('database.no_data') || '暂无数据'}</p>`;
            return;
        }
        let html = `<table style="width:100%;border-collapse:collapse;font-size:12px;">
            <tr style="border-bottom:1px solid var(--border);">
                <th style="text-align:left;padding:4px 6px;">日期</th>
                <th style="text-align:left;padding:4px 6px;">应用</th>
                <th style="text-align:left;padding:4px 6px;">分类</th>
                <th style="text-align:right;padding:4px 6px;">时长(分)</th>
                <th style="text-align:right;padding:4px 6px;">会话数</th>
            </tr>`;
        records.forEach(r => {
            const mins = Math.round(r.duration_seconds / 60);
            html += `<tr style="border-bottom:1px solid var(--border);color:var(--text-secondary);">
                <td style="padding:4px 6px;">${r.date}</td>
                <td style="padding:4px 6px;">${r.app_name}</td>
                <td style="padding:4px 6px;">${r.category}</td>
                <td style="text-align:right;padding:4px 6px;">${mins}</td>
                <td style="text-align:right;padding:4px 6px;">${r.session_count}</td>
            </tr>`;
        });
        html += '</table>';
        tableEl.innerHTML = html;
    } catch (e) {
        console.error('[loadDatabasePreview] error:', e);
    }
}

const btnCleanupDb = document.getElementById('btn-cleanup-db');
if (btnCleanupDb) {
    btnCleanupDb.addEventListener('click', async () => {
        const days = document.getElementById('cleanup-days').value || 90;
        if (!confirm(`确定要清理 ${days} 天前的数据吗？`)) return;
        try {
            const data = await API.post('/api/database', { action: 'cleanup', days: parseInt(days) });
            toast(data && data.ok ? `✅ ${t('toast.removed')}` : `❌ ${data ? data.msg : 'Failed'}`);
            loadDatabaseInfo();
        } catch (e) {
            toast('❌ ' + e.message);
        }
    });
}

const btnBackupDb = document.getElementById('btn-backup-db');
if (btnBackupDb) {
    btnBackupDb.addEventListener('click', async () => {
        try {
            const data = await API.post('/api/database', { action: 'backup' });
            toast(data && data.ok ? '✅ Backup successful' : `❌ ${data ? data.msg : 'Failed'}`);
        } catch (e) {
            toast('❌ ' + e.message);
        }
    });
}

/* ---- Feedback ---- */
let _currentLogFile = null;

async function loadCrashLogs() {
    try {
        const data = await API.get('/api/feedback/logs');
        if (!data || !data.ok) return;
        const list = document.getElementById('crash-logs-list');
        if (!list) return;
        list.innerHTML = '';
        const logs = data.logs || [];
        if (logs.length === 0) {
            list.innerHTML = `<p style="color:var(--text-secondary);font-size:13px;">${t('feedback.no_logs')}</p>`;
            return;
        }
        logs.forEach(log => {
            const div = document.createElement('div');
            div.className = 'app-item clickable';
            const sizeStr = log.size > 1024 ? Math.round(log.size / 1024) + ' KB' : log.size + ' B';
            div.innerHTML = `
                <span class="app-name">${log.name}</span>
                <span class="app-path">${sizeStr}</span>
            `;
            div.addEventListener('click', () => {
                _currentLogFile = log.name;
                // Highlight selected
                list.querySelectorAll('.app-item').forEach(el => el.style.background = '');
                div.style.background = 'var(--accent-dim, rgba(30,144,255,0.1))';
                readLogFile(log.name);
            });
            list.appendChild(div);
        });
    } catch (e) {
        console.error('[loadCrashLogs] error:', e);
    }
}

async function readLogFile(filename) {
    const logContent = document.getElementById('log-content');
    const logInfo = document.getElementById('log-info');
    if (!logContent) return;
    try {
        const data = await API.get(`/api/feedback/logs/read?file=${encodeURIComponent(filename)}`);
        if (!data || !data.ok) {
            logContent.textContent = 'Failed to read log';
            return;
        }
        if (logInfo) logInfo.textContent = `${filename} (${data.total_lines} lines, showing last ${data.content.split('\n').length})`;
        logContent.textContent = data.content;
        logContent.style.display = 'block';
    } catch (e) {
        logContent.textContent = 'Error: ' + e.message;
        logContent.style.display = 'block';
    }
}

const btnSubmitFeedback = document.getElementById('btn-submit-feedback');
if (btnSubmitFeedback) {
    btnSubmitFeedback.addEventListener('click', async () => {
        const desc = document.getElementById('feedback-desc').value.trim();
        if (!desc) { toast(t('toast.empty')); return; }
        const contact = document.getElementById('feedback-contact').value.trim();
        try {
            const data = await API.post('/api/feedback', { description: desc, contact });
            if (data && data.ok) {
                toast('✅ ' + (data.msg || t('feedback.submit')));
                document.getElementById('feedback-desc').value = '';
                document.getElementById('feedback-contact').value = '';
            } else {
                toast('❌ ' + (data ? data.msg : 'Failed'));
            }
        } catch (e) {
            toast('❌ ' + e.message);
        }
    });
}

// 打开反馈文件夹
const btnOpenFeedbackDir = document.getElementById('btn-open-feedback-dir');
if (btnOpenFeedbackDir) {
    btnOpenFeedbackDir.addEventListener('click', async () => {
        try {
            await API.get('/api/feedback/open-dir');
        } catch (e) {
            toast('❌ ' + e.message);
        }
    });
}

// 日志等级切换
const cfgLogLevel = document.getElementById('cfg-log-level');
if (cfgLogLevel) {
    // 初始化当前等级
    API.get('/api/log-level').then(data => {
        if (data && data.ok && data.level) cfgLogLevel.value = data.level;
    }).catch(() => {});
    cfgLogLevel.addEventListener('change', async () => {
        try {
            const data = await API.post('/api/log-level', { level: cfgLogLevel.value });
            toast(data && data.ok ? '✅ ' + data.msg : '❌ Failed');
        } catch (e) {
            toast('❌ ' + e.message);
        }
    });
}

/* ---- Init ---- */
window.addEventListener('DOMContentLoaded', () => {
    console.log('[App] DOMContentLoaded, loading settings...');
    loadGeneralSettings();
});
