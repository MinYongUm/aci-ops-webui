// ============================================================
// interface.js — Interface Monitor 섹션
// 버전: v1.8.0 — scaffold inject 방식으로 변경
// 의존: common.js (apiFetch, setEl, escHtml, miniStatCard,
//                  showLoading)
// ============================================================

function _buildInterfaceScaffold() {
    return [
        // ---- 요약 + 프로그레스 ----
        '<div class="card mb-4">',
        '  <div class="card-header"><i class="bi bi-ethernet me-2"></i>INTERFACE STATUS</div>',
        '  <div class="card-body" id="iface-summary-content">',
        '    <div class="text-muted text-center py-3">Loading...</div>',
        '  </div>',
        '</div>',

        // ---- Down Reasons ----
        '<div class="card">',
        '  <div class="card-header"><i class="bi bi-x-circle me-2"></i>DOWN REASONS</div>',
        '  <div class="card-body p-0">',
        '    <div class="table-responsive">',
        '      <table class="table table-sm mb-0">',
        '        <thead><tr><th>REASON</th><th class="text-end">COUNT</th></tr></thead>',
        '        <tbody id="iface-reasons-tbody">',
        '          <tr><td colspan="2" class="text-center text-muted py-3">Loading...</td></tr>',
        '        </tbody>',
        '      </table>',
        '    </div>',
        '  </div>',
        '</div>'
    ].join('\n');
}

async function loadInterface() {
    var body = document.getElementById('section-body');
    if (body) body.innerHTML = _buildInterfaceScaffold();

    showLoading(true);
    try {
        var data = await apiFetch('/api/interface');
        renderInterface(data);
    } catch (e) {
        console.error('Interface load error:', e);
    }
    showLoading(false);
}

function renderInterface(data) {
    var upPct   = data.total > 0 ? ((data.up / data.total) * 100).toFixed(1) : 0;
    var downPct = (100 - upPct).toFixed(1);

    // ---- 요약 + 프로그레스 바 ----
    var summaryHtml =
        '<div class="row g-2 mb-3">' +
        miniStatCard('Total', data.total) +
        miniStatCard('Up',    data.up,   'state-ok') +
        miniStatCard('Down',  data.down, data.down > 0 ? 'state-warn' : '') +
        '</div>' +
        '<div class="progress mb-1">' +
        '<div class="progress-bar bg-success" style="width:' + upPct   + '%"></div>' +
        '<div class="progress-bar bg-danger"  style="width:' + downPct + '%"></div>' +
        '</div>' +
        '<div style="font-size:14px;color:var(--text-muted);font-family:monospace">' +
        upPct + '% up</div>';
    setEl('iface-summary-content', summaryHtml, true);

    // ---- Down Reasons 테이블 ----
    var reasonsHtml = data.down_reasons.length === 0
        ? '<tr><td colspan="2" class="text-center text-muted py-3">No down interfaces</td></tr>'
        : data.down_reasons.map(function (r) {
            return '<tr>' +
                '<td><code>' + escHtml(r.reason) + '</code></td>' +
                '<td class="text-end"><span class="sev sev-major">' + r.count + '</span></td>' +
                '</tr>';
          }).join('');
    setEl('iface-reasons-tbody', reasonsHtml, true);
}