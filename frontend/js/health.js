// ============================================================
// health.js — Health Check 섹션
// 의존: common.js (apiFetch, setEl, escHtml, showLoading,
//                  cachedFaults)
// ============================================================

async function loadHealth() {
    showLoading(true);
    try {
        var data = await apiFetch('/api/health');
        renderHealth(data);
    } catch (e) {
        console.error('Health load error:', e);
    }
    showLoading(false);
}

function renderHealth(data) {
    cachedFaults = data.critical_major;

    // ---- Severity 요약 카드 ----
    var sevHtml =
        '<div class="row g-2 mb-3">' +
        sevCard('Critical', data.severity.critical, 'color-critical') +
        sevCard('Major',    data.severity.major,    'color-major')    +
        sevCard('Minor',    data.severity.minor,    'color-minor')    +
        sevCard('Warning',  data.severity.warning,  'text-muted')     +
        '</div>';
    setEl('health-severity-content', sevHtml, true);

    // ---- 노드 상태 ----
    var nodeHtml = '';
    if (!data.nodes) {
        nodeHtml = '<div class="text-muted">Node data unavailable</div>';
    } else {
        nodeHtml =
            '<div class="d-flex gap-2 flex-wrap">' +
            '<div class="node-chip"><div class="dot dot-up"></div>Up: '   + data.nodes.up   + '</div>' +
            '<div class="node-chip"><div class="dot dot-down"></div>Down: ' + data.nodes.down + '</div>' +
            '</div>';
    }
    setEl('health-nodes-content', nodeHtml, true);

    // ---- Critical / Major Fault 목록 ----
    var faultHtml = '';
    if (data.critical_major.length === 0) {
        faultHtml = '<tr><td colspan="2" class="text-center py-3">' +
            '<span class="sev sev-minor">All Systems Normal</span></td></tr>';
    } else {
        data.critical_major.forEach(function (f, idx) {
            var sevClass = f.severity === 'CRITICAL' ? 'sev-critical' : 'sev-major';
            faultHtml +=
                '<tr style="cursor:pointer" onclick="showFaultDetail(' + idx + ')">' +
                '<td><span class="sev ' + sevClass + '">' + f.severity + '</span></td>' +
                '<td>' + escHtml(f.description) + '</td>' +
                '</tr>';
        });
    }
    setEl('health-faults-tbody', faultHtml, true);
}

function sevCard(label, count, colorVar) {
    return '<div class="col-6 col-md-3">' +
        '<div class="stat-card text-center p-2">' +
        '<div style="font-size:22px;font-weight:700;color:var(--' + colorVar + ');font-family:var(--font-mono)">' + count + '</div>' +
        '<div style="font-size:14px;color:var(--text-muted);text-transform:uppercase">' + label + '</div>' +
        '</div></div>';
}

function showFaultDetail(idx) {
    var fault = cachedFaults[idx];
    if (!fault) return;
    var sevClass = fault.severity === 'CRITICAL' ? 'sev-critical' : 'sev-major';
    document.getElementById('fault-modal-body').innerHTML =
        '<div class="mb-3"><span class="sev ' + sevClass + ' fs-6">' + fault.severity + '</span></div>' +
        '<p style="font-size:14px;">' + escHtml(fault.description) + '</p>';
    new bootstrap.Modal(document.getElementById('faultModal')).show();
}