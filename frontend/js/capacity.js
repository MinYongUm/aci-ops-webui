// ============================================================
// capacity.js — Capacity Report 섹션
// 의존: common.js (apiFetch, setEl, escHtml, showLoading)
// ============================================================

async function loadCapacity() {
    showLoading(true);
    try {
        var data = await apiFetch('/api/capacity');
        renderCapacity(data);
    } catch (e) {
        console.error('Capacity load error:', e);
    }
    showLoading(false);
}

function renderCapacity(data) {
    // ---- Alert 박스 ----
    var alertHtml = data.high_usage_count > 0
        ? '<div class="critical-box"><i class="bi bi-exclamation-triangle me-1"></i>' +
          data.high_usage_count + ' node(s) with TCAM usage >= 80%. Immediate action required.</div>'
        : '<div class="ok-box"><i class="bi bi-check-circle me-1"></i>All nodes within normal TCAM capacity.</div>';
    setEl('capacity-alert-box', alertHtml, true);

    // ---- TCAM 테이블 ----
    var tableHtml = data.tcam.length === 0
        ? '<tr><td colspan="4" class="text-center text-muted py-3">No TCAM data</td></tr>'
        : data.tcam.map(function (t) {
            var pctClass = t.percentage >= 80 ? 'bg-danger' :
                           t.percentage >= 50 ? 'bg-warning' : 'bg-success';
            var sevClass = t.percentage >= 80 ? 'sev-critical' :
                           t.percentage >= 50 ? 'sev-major' : 'sev-minor';
            return '<tr>' +
                '<td><code>' + escHtml(t.node) + '</code></td>' +
                '<td class="text-end">' + t.used.toLocaleString()     + '</td>' +
                '<td class="text-end">' + t.capacity.toLocaleString() + '</td>' +
                '<td>' +
                '<div class="d-flex align-items-center gap-2">' +
                '<div class="progress flex-grow-1">' +
                '<div class="progress-bar ' + pctClass + '" style="width:' + t.percentage + '%"></div>' +
                '</div>' +
                '<span class="sev ' + sevClass + '" style="width:40px;text-align:right">' + t.percentage + '%</span>' +
                '</div>' +
                '</td>' +
                '</tr>';
          }).join('');
    setEl('capacity-tbody', tableHtml, true);
}