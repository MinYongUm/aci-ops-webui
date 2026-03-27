// ============================================================
// common.js — 공통 상태, 네비게이션, 유틸리티
// 버전: v1.9.1 — Settings 섹션 추가
//
// 로딩 순서: 반드시 모든 모듈별 JS보다 먼저 로드
// ============================================================

// ============================================================
// SECTION METADATA (v1.8.0: 섹션 타이틀 + 부제목)
// v1.9.1: settings 항목 추가
// ============================================================
var SECTION_META = {
    dashboard:  { title: 'Dashboard',          subtitle: 'ACI Fabric 운영 현황 요약' },
    health:     { title: 'Health Check',       subtitle: 'Fault 및 노드 상태 모니터링' },
    policy:     { title: 'Policy Check',       subtitle: 'Contract 정책 검증 및 보안 감사' },
    interface:  { title: 'Interface Monitor',  subtitle: '물리 인터페이스 상태 및 에러 분석' },
    endpoint:   { title: 'Endpoint Tracker',   subtitle: 'MAC / IP 기반 Endpoint 위치 추적' },
    audit:      { title: 'Audit Log',          subtitle: 'APIC 설정 변경 이력 조회' },
    capacity:   { title: 'Capacity Report',    subtitle: 'TCAM 용량 사용률 모니터링' },
    topology:   { title: 'Topology Viewer',    subtitle: 'Spine-Leaf Fabric 토폴로지 시각화' },
    linter:     { title: 'Config Linter',      subtitle: 'ACI 정책 오류 및 Best Practice 검증' },
    simulator:  { title: 'Microseg Simulator', subtitle: 'EPG 간 트래픽 허용/차단 정책 시뮬레이션' },
    settings:   { title: 'Settings',           subtitle: 'APIC 연결 설정 관리' }
};

// ============================================================
// STATE
// ============================================================

// ============================================================
// [BUG FIX v1.8.0]
// 기존: var currentSection = 'dashboard'
// 문제: 페이지 로드 시 init block이 navigateTo('dashboard') 호출
//       → section === currentSection ('dashboard' === 'dashboard') 조건 true
//       → refreshCurrent() 경로로 진입 → loadDashboard() 중복 실행
//       → /api/all 이 정상 경로 + refreshCurrent() 경로로 중복 호출됨
// 수정: null로 초기화
//       첫 navigateTo('dashboard') 호출 시 null !== 'dashboard' → 정상 경로만 실행
// ============================================================
var currentSection   = null;
var autoRefreshTimer = null;
var cachedAll        = null;   // /api/all 응답 캐시 (CSV 내보내기용)
var simTenants       = [];     // 시뮬레이터 Tenant 목록 캐시
var cachedFaults     = [];     // Health 섹션 Fault 상세 (모달용)

// ============================================================
// NAVIGATION
// ============================================================
function navigateTo(section) {
    // --------------------------------------------------------
    // 같은 섹션 재클릭 → 단순 새로고침 (정상 동작)
    // 초기 로드 시에는 currentSection = null 이므로 이 분기 미실행
    // --------------------------------------------------------
    if (section === currentSection) {
        refreshCurrent();
        return;
    }

    currentSection = section;

    // 사이드바 active 상태 (v1.8.0: id="nav-{section}" 구조)
    document.querySelectorAll('.nav-item').forEach(function (el) {
        el.classList.toggle('active', el.id === 'nav-' + section);
    });

    // 섹션 헤더 타이틀 + 부제목 업데이트 (v1.8.0 신규)
    var meta = SECTION_META[section];
    if (meta) {
        var titleEl    = document.getElementById('section-title');
        var subtitleEl = document.getElementById('section-subtitle');
        if (titleEl)    titleEl.textContent    = meta.title;
        if (subtitleEl) subtitleEl.textContent = meta.subtitle;
    }

    // 데이터 로드
    loadSection(section);
}

function refreshCurrent() {
    loadSection(currentSection);
}

// ============================================================
// DATA LOADING — 섹션별 분기
// v1.9.1: settings 케이스 추가
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
        case 'settings':   return loadSettings();
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

    // v1.8.0: 사이드바 푸터의 last-update 단일 엘리먼트
    var lastUpdateEl = document.getElementById('last-update');
    if (lastUpdateEl) lastUpdateEl.textContent = t;

    // v1.6.0 이전 호환 (last-update-side, last-update-top)
    setEl('last-update-side', t);
    setEl('last-update-top', 'Updated: ' + t);
}

function updateConnectionStatus(ok) {
    var dot   = document.getElementById('conn-dot');
    var label = document.getElementById('conn-label');
    if (!dot || !label) return;

    // v1.8.0: connected / disconnected 클래스 사용
    dot.className     = 'conn-dot ' + (ok ? 'connected' : 'disconnected');
    label.textContent = ok ? 'Connected' : 'Disconnected';
}

function showLoading(show) {
    var el = document.getElementById('loading-overlay');
    if (!el) return;
    el.style.display = show ? 'flex' : 'none';
}

// ============================================================
// AUTO-REFRESH
// ============================================================
function setupAutoRefresh() {
    var checkbox = document.getElementById('autoRefresh');
    if (!checkbox) return;

    checkbox.addEventListener('change', function () {
        clearInterval(autoRefreshTimer);
        if (this.checked) startAutoRefresh();
    });
    startAutoRefresh();
}

function startAutoRefresh() {
    autoRefreshTimer = setInterval(function () {
        // Linter, Settings는 자동 새로고침 제외
        if (currentSection !== 'linter' && currentSection !== 'settings') {
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
    csv += 'Health,Total Faults,'       + d.health.total_faults         + '\n';
    csv += 'Health,Critical,'           + d.health.severity.critical     + '\n';
    csv += 'Health,Major,'              + d.health.severity.major        + '\n';
    csv += 'Health,Minor,'              + d.health.severity.minor        + '\n';
    csv += 'Health,Warning,'            + d.health.severity.warning      + '\n';
    csv += 'Health,Nodes Up,'           + d.health.nodes.up              + '\n';
    csv += 'Health,Nodes Down,'         + d.health.nodes.down            + '\n';
    csv += 'Policy,Security Risks,'     + d.policy.security_risks        + '\n';
    csv += 'Policy,Total Tenants,'      + d.policy.total_tenants         + '\n';
    csv += 'Policy,Total Contracts,'    + d.policy.total_contracts       + '\n';
    csv += 'Interface,Total,'           + d.interface.total              + '\n';
    csv += 'Interface,Up,'              + d.interface.up                 + '\n';
    csv += 'Interface,Down,'            + d.interface.down               + '\n';
    csv += 'Endpoint,Total,'            + d.endpoint.total               + '\n';
    csv += 'Capacity,High Usage Nodes,' + d.capacity.high_usage_count    + '\n';
    csv += 'Topology,Controllers,'      + d.topology.summary.controllers + '\n';
    csv += 'Topology,Spines,'           + d.topology.summary.spines      + '\n';
    csv += 'Topology,Leafs,'            + d.topology.summary.leafs       + '\n';

    var blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    var a    = document.createElement('a');
    a.href     = URL.createObjectURL(blob);
    a.download = 'aci-report-' + new Date().toISOString().slice(0, 10) + '.csv';
    a.click();
}