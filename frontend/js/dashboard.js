// ============================================================
// dashboard.js — Dashboard 섹션
// 버전: v1.8.0 — section-body 동적 scaffold inject 방식으로 변경
//
// 변경 이유:
//   v1.8.0 index.html이 섹션별 pre-defined HTML 구조를 제거하고
//   단일 section-body 컨테이너로 교체함에 따라,
//   setEl() 타겟 element가 존재하지 않아 화면이 비어있던 버그 수정.
//   loadDashboard() 진입 시 scaffold HTML을 먼저 inject한 뒤 데이터 채움.
//
// 의존: common.js (apiFetch, setEl, escHtml, actionBadge,
//                  updateBadge, updateTimestamp,
//                  updateConnectionStatus, showLoading,
//                  cachedAll, navigateTo)
// ============================================================

// ============================================================
// SCAFFOLD — Dashboard 섹션 HTML 구조
// section-body에 inject. 이후 setEl()로 각 element 데이터 채움.
// ============================================================
function _buildDashboardScaffold() {
    return [
        // ---- Stat cards ----
        '<div class="row g-3 mb-4">',

        '  <div class="col-6 col-xl-3">',
        '    <div class="card stat-card" id="stat-card-faults">',
        '      <div class="stat-value text-danger" id="s-total-faults">-</div>',
        '      <div class="stat-label">Total Faults</div>',
        '      <div style="font-size:0.72rem;color:var(--text-dim);margin-top:4px" id="s-faults-sub"></div>',
        '    </div>',
        '  </div>',

        '  <div class="col-6 col-xl-3">',
        '    <div class="card stat-card">',
        '      <div class="stat-value text-cisco" id="s-nodes">-</div>',
        '      <div class="stat-label">Nodes Up</div>',
        '    </div>',
        '  </div>',

        '  <div class="col-6 col-xl-3">',
        '    <div class="card stat-card">',
        '      <div class="stat-value text-info" id="s-iface">-</div>',
        '      <div class="stat-label">Interfaces Up</div>',
        '    </div>',
        '  </div>',

        '  <div class="col-6 col-xl-3">',
        '    <div class="card stat-card">',
        '      <div class="stat-value text-success" id="s-endpoints">-</div>',
        '      <div class="stat-label">Endpoints</div>',
        '    </div>',
        '  </div>',

        '  <div class="col-6 col-xl-3">',
        '    <div class="card stat-card">',
        '      <div class="stat-value text-warning" id="s-risks">-</div>',
        '      <div class="stat-label">Security Risks</div>',
        '    </div>',
        '  </div>',

        '  <div class="col-6 col-xl-3">',
        '    <div class="card stat-card">',
        '      <div class="stat-value text-danger" id="s-capacity">-</div>',
        '      <div class="stat-label">High TCAM Nodes</div>',
        '    </div>',
        '  </div>',

        '</div>',

        // ---- Module status grid ----
        '<div class="card mb-4">',
        '  <div class="card-header">',
        '    <i class="bi bi-grid me-2"></i>',
        '    MODULE STATUS',
        '    <span style="font-size:0.72rem;font-weight:400;color:var(--text-muted);margin-left:8px">— CLICK TO OPEN</span>',
        '  </div>',
        '  <div class="card-body">',
        '    <div class="module-grid" id="module-grid"></div>',
        '  </div>',
        '</div>',

        // ---- Recent changes ----
        '<div class="card">',
        '  <div class="card-header">',
        '    <i class="bi bi-clock-history me-2"></i>RECENT CHANGES',
        '  </div>',
        '  <div class="card-body p-0">',
        '    <div class="table-responsive">',
        '      <table class="table table-sm mb-0">',
        '        <thead>',
        '          <tr>',
        '            <th>TIMESTAMP</th>',
        '            <th>USER</th>',
        '            <th>ACTION</th>',
        '            <th>AFFECTED OBJECT</th>',
        '          </tr>',
        '        </thead>',
        '        <tbody id="dash-audit-tbody">',
        '          <tr><td colspan="4" class="text-center text-muted py-3">Loading...</td></tr>',
        '        </tbody>',
        '      </table>',
        '    </div>',
        '  </div>',
        '</div>'
    ].join('\n');
}

// ============================================================
// LOAD
// ============================================================
async function loadDashboard() {
    // section-body에 scaffold inject (매번 재생성 — 데이터 갱신 시 깨끗하게 초기화)
    var body = document.getElementById('section-body');
    if (body) body.innerHTML = _buildDashboardScaffold();

    showLoading(true);
    try {
        var data = await apiFetch('/api/all');
        cachedAll = data;
        renderDashboard(data);
        updateConnectionStatus(true);
    } catch (e) {
        console.error('Dashboard load error:', e);
        updateConnectionStatus(false);
    }
    showLoading(false);
}

// ============================================================
// RENDER
// ============================================================
function renderDashboard(data) {
    var h = data.health;
    var p = data.policy;
    var i = data.interface;
    var e = data.endpoint;
    var a = data.audit;
    var c = data.capacity;
    var t = data.topology;

    // ---- Stat cards ----
    var critMaj = h.severity.critical + h.severity.major;
    setEl('s-total-faults', h.total_faults);
    setEl('s-faults-sub',
        'C:' + h.severity.critical +
        ' M:' + h.severity.major +
        ' m:' + h.severity.minor +
        ' W:' + h.severity.warning);
    setEl('s-nodes',     h.nodes.up + ' / ' + (h.nodes.up + h.nodes.down));
    setEl('s-iface',     i.up + ' / ' + i.total);
    setEl('s-endpoints', e.total.toLocaleString());
    setEl('s-risks',     p.security_risks);
    setEl('s-capacity',  c.high_usage_count);

    // Fault stat card 배경 강조
    var faultCard = document.getElementById('stat-card-faults');
    if (faultCard) {
        faultCard.className = 'card stat-card' +
            (h.severity.critical > 0 ? ' state-critical' :
             h.severity.major    > 0 ? ' state-warn' : '');
    }

    // ---- 사이드바 배지 ----
    updateBadge('health',   critMaj,            'err');
    updateBadge('policy',   p.security_risks,   'warn');
    updateBadge('capacity', c.high_usage_count, 'err');

    // ---- Module status grid ----
    var modules = [
        {
            section: 'health',
            icon:    'bi-heart-pulse',
            name:    'Health Check',
            status:  h.severity.critical > 0 ? 'mod-critical' :
                     h.severity.major    > 0 ? 'mod-warn' : 'mod-ok',
            value:   critMaj > 0 ? critMaj + ' fault(s)' : 'All clear'
        },
        {
            section: 'policy',
            icon:    'bi-shield-exclamation',
            name:    'Policy Check',
            status:  p.security_risks > 0 ? 'mod-warn' : 'mod-ok',
            value:   p.security_risks > 0 ? p.security_risks + ' risk(s)' : 'Clean'
        },
        {
            section: 'interface',
            icon:    'bi-ethernet',
            name:    'Interface',
            status:  i.down > 0 ? 'mod-warn' : 'mod-ok',
            value:   i.up + ' up / ' + i.down + ' down'
        },
        {
            section: 'endpoint',
            icon:    'bi-hdd-network',
            name:    'Endpoint',
            status:  'mod-neutral',
            value:   e.total.toLocaleString() + ' total'
        },
        {
            section: 'audit',
            icon:    'bi-clock-history',
            name:    'Audit Log',
            status:  'mod-neutral',
            value:   a.total + ' recent changes'
        },
        {
            section: 'capacity',
            icon:    'bi-bar-chart-line',
            name:    'Capacity',
            status:  c.high_usage_count > 0 ? 'mod-critical' : 'mod-ok',
            value:   c.high_usage_count > 0 ?
                     c.high_usage_count + ' node(s) high' : 'Normal'
        },
        {
            section: 'topology',
            icon:    'bi-diagram-3',
            name:    'Topology',
            status:  h.nodes.down > 0 ? 'mod-warn' : 'mod-ok',
            value:   t.summary.controllers + 'C / ' +
                     t.summary.spines      + 'S / ' +
                     t.summary.leafs       + 'L'
        }
    ];

    var gridHtml = '';
    modules.forEach(function (m) {
        gridHtml +=
            '<div class="module-card ' + m.status + '" onclick="navigateTo(\'' + m.section + '\')">' +
            '<span class="mod-icon"><i class="bi ' + m.icon + '"></i></span>' +
            '<div class="mod-info">' +
            '<div class="mod-name">'  + m.name  + '</div>' +
            '<div class="mod-value">' + m.value + '</div>' +
            '</div></div>';
    });
    setEl('module-grid', gridHtml, true);

    // ---- Recent audit ----
    var auditHtml = '';
    if (a.recent.length === 0) {
        auditHtml = '<tr><td colspan="4" class="text-center text-muted py-3">No recent changes</td></tr>';
    } else {
        a.recent.slice(0, 5).forEach(function (r) {
            auditHtml +=
                '<tr>' +
                '<td><code>' + escHtml(r.timestamp) + '</code></td>' +
                '<td>' + escHtml(r.user) + '</td>' +
                '<td>' + actionBadge(r.action) + '</td>' +
                '<td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap"' +
                ' title="' + escHtml(r.affected) + '">' + escHtml(r.affected) + '</td>' +
                '</tr>';
        });
    }
    setEl('dash-audit-tbody', auditHtml, true);

    updateTimestamp();
}