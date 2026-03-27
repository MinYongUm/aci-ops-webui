// ============================================================
// common.js — 공통 상태, 네비게이션, 유틸리티
// 로딩 순서: 반드시 모든 모듈별 JS보다 먼저 로드
// ============================================================

// ============================================================
// CONSTANTS
// ============================================================
var SECTION_TITLES = {
    dashboard:  'Dashboard',
    health:     'Health Check',
    policy:     'Policy Check',
    interface:  'Interface Monitor',
    endpoint:   'Endpoint Tracker',
    audit:      'Audit Log',
    capacity:   'Capacity Report',
    topology:   'Topology Viewer',
    linter:     'Config Linter',
    simulator:  'Microseg Simulator'
};

// ============================================================
// STATE
// ============================================================
var currentSection   = 'dashboard';
var autoRefreshTimer = null;
var cachedAll        = null;   // /api/all 응답 캐시 (CSV 내보내기용)
var simTenants       = [];     // 시뮬레이터 Tenant 목록 캐시
var cachedFaults     = [];     // Health 섹션 Fault 상세 (모달용)

// ============================================================
// NAVIGATION
// ============================================================
function navigateTo(section) {
    if (section === currentSection) { refreshCurrent(); return; }

    currentSection = section;

    // 사이드바 active 상태
    document.querySelectorAll('.sidebar-nav-item').forEach(function (el) {
        el.classList.toggle('active', el.dataset.section === section);
    });

    // 섹션 표시
    document.querySelectorAll('.page-section').forEach(function (el) {
        el.classList.toggle('active', el.id === 'section-' + section);
    });

    // Topbar 제목
    document.getElementById('topbar-title').textContent = SECTION_TITLES[section];

    // 데이터 로드
    loadSection(section);
}

function refreshCurrent() {
    loadSection(currentSection);
}

// ============================================================
// DATA LOADING — 섹션별 분기
// ============================================================
function loadSection(section) {
    switch (section) {
        case 'dashboard':  return loadDashboard();
        case 'health':     return loadHealth();
        case 'policy':     return loadPolicy();
        case 'interface':  return loadInterface();
        case 'endpoint':   return loadEndpoint();
        case 'audit':      return loadAudit();
        case 'capacity':   return loadCapacity();
        case 'topology':   return loadTopology();
        case 'simulator':  return loadSimulatorTenants();
        case 'linter':     return;  // 수동 트리거만
    }
}

// ============================================================
// FETCH HELPER
// ============================================================
async function apiFetch(url, options) {
    options = options || {};
    var res = await fetch(url, options);
    if (!res.ok) throw new Error('HTTP ' + res.status);
    return res.json();
}

// ============================================================
// UTILITY FUNCTIONS
// ============================================================
function setEl(id, content, isHtml) {
    var el = document.getElementById(id);
    if (!el) return;
    if (isHtml) el.innerHTML = content;
    else el.textContent = content;
}

function escHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function actionBadge(action) {
    var map = {
        creation:     ['sev-minor',    'Creation'],
        modification: ['sev-major',    'Modification'],
        deletion:     ['sev-critical', 'Deletion']
    };
    var pair  = map[action] || ['sev-warning', action];
    var cls   = pair[0];
    var label = pair[1];
    return '<span class="sev ' + cls + '">' + label + '</span>';
}

function miniStatCard(label, value, extraClass) {
    extraClass = extraClass || '';
    return '<div class="col-6 col-md-3">' +
        '<div class="stat-card text-center p-2 ' + extraClass + '">' +
        '<div style="font-size:22px;font-weight:700;font-family:var(--font-mono)">' + value + '</div>' +
        '<div style="font-size:14px;color:var(--text-muted);text-transform:uppercase">' + label + '</div>' +
        '</div></div>';
}

function updateBadge(section, count, type) {
    var el = document.getElementById('badge-' + section);
    if (!el) return;
    if (count > 0) {
        el.textContent = count;
        el.classList.remove('d-none');
        el.className = type === 'warn' ? 'nav-badge warn' : 'nav-badge';
    } else {
        el.classList.add('d-none');
    }
}

function updateTimestamp() {
    var t = new Date().toLocaleTimeString();
    setEl('last-update-side', t);
    setEl('last-update-top', 'Updated: ' + t);
}

function updateConnectionStatus(ok) {
    var dot   = document.getElementById('conn-dot');
    var label = document.getElementById('conn-label');
    dot.className   = ok ? 'conn-dot' : 'conn-dot off';
    label.textContent = ok ? 'Connected' : 'Disconnected';
}

function showLoading(show) {
    document.getElementById('loading-overlay').style.display = show ? 'flex' : 'none';
}

// ============================================================
// AUTO-REFRESH
// ============================================================
function setupAutoRefresh() {
    var checkbox = document.getElementById('autoRefresh');
    checkbox.addEventListener('change', function () {
        clearInterval(autoRefreshTimer);
        if (this.checked) startAutoRefresh();
    });
    startAutoRefresh();
}

function startAutoRefresh() {
    autoRefreshTimer = setInterval(function () {
        if (currentSection !== 'linter') {  // Linter는 수동 전용
            loadSection(currentSection);
        }
    }, 30000);
}

// ============================================================
// CSV EXPORT — 캐시된 Dashboard 데이터 기준
// ============================================================
function exportCSV() {
    if (!cachedAll) { alert('Dashboard 데이터를 먼저 로드하세요.'); return; }
    var d = cachedAll;

    var csv = 'Category,Metric,Value\n';
    csv += 'Health,Total Faults,'       + d.health.total_faults        + '\n';
    csv += 'Health,Critical,'           + d.health.severity.critical    + '\n';
    csv += 'Health,Major,'              + d.health.severity.major       + '\n';
    csv += 'Health,Minor,'              + d.health.severity.minor       + '\n';
    csv += 'Health,Warning,'            + d.health.severity.warning     + '\n';
    csv += 'Health,Nodes Up,'           + d.health.nodes.up             + '\n';
    csv += 'Health,Nodes Down,'         + d.health.nodes.down           + '\n';
    csv += 'Policy,Security Risks,'     + d.policy.security_risks       + '\n';
    csv += 'Policy,Total Tenants,'      + d.policy.total_tenants        + '\n';
    csv += 'Policy,Total Contracts,'    + d.policy.total_contracts      + '\n';
    csv += 'Interface,Total,'           + d.interface.total             + '\n';
    csv += 'Interface,Up,'              + d.interface.up                + '\n';
    csv += 'Interface,Down,'            + d.interface.down              + '\n';
    csv += 'Endpoint,Total,'            + d.endpoint.total              + '\n';
    csv += 'Capacity,High Usage Nodes,' + d.capacity.high_usage_count   + '\n';
    csv += 'Topology,Controllers,'      + d.topology.summary.controllers + '\n';
    csv += 'Topology,Spines,'           + d.topology.summary.spines     + '\n';
    csv += 'Topology,Leafs,'            + d.topology.summary.leafs      + '\n';

    var blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    var a    = document.createElement('a');
    a.href     = URL.createObjectURL(blob);
    a.download = 'aci-report-' + new Date().toISOString().slice(0, 10) + '.csv';
    a.click();
}