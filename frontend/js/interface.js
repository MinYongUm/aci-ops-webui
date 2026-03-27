// ============================================================
// interface.js — Interface Monitor 섹션
// 의존: common.js (apiFetch, setEl, escHtml, miniStatCard,
//                  showLoading)
// ============================================================

async function loadInterface() {
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
        '<div style="font-size:14px;color:var(--text-muted);font-family:var(--font-mono)">' +
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