// ============================================================
// dashboard.js — Dashboard 섹션
// 의존: common.js (apiFetch, setEl, escHtml, actionBadge,
//                  updateBadge, updateTimestamp,
//                  updateConnectionStatus, showLoading,
//                  cachedAll, navigateTo)
// ============================================================

async function loadDashboard() {
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
    var faultCard = document.getElementById('s-total-faults').closest('.stat-card');
    faultCard.className = 'stat-card' +
        (h.severity.critical > 0 ? ' state-critical' :
         h.severity.major    > 0 ? ' state-warn' : '');

    // ---- 사이드바 배지 ----
    updateBadge('health',   critMaj,              'err');
    updateBadge('policy',   p.security_risks,     'warn');
    updateBadge('capacity', c.high_usage_count,   'err');

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