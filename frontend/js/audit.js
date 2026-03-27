// ============================================================
// audit.js — Audit Log 섹션
// 버전: v1.8.0 — scaffold inject 방식으로 변경
// 의존: common.js (apiFetch, setEl, escHtml, actionBadge,
//                  showLoading)
// ============================================================

function _buildAuditScaffold() {
    return [
        // ---- 사용자별 변경 횟수 ----
        '<div class="card mb-4">',
        '  <div class="card-header"><i class="bi bi-person me-2"></i>CHANGES BY USER</div>',
        '  <div class="card-body p-0">',
        '    <div class="table-responsive">',
        '      <table class="table table-sm mb-0">',
        '        <thead><tr><th>USER</th><th class="text-end">COUNT</th></tr></thead>',
        '        <tbody id="audit-user-tbody">',
        '          <tr><td colspan="2" class="text-center text-muted py-3">Loading...</td></tr>',
        '        </tbody>',
        '      </table>',
        '    </div>',
        '  </div>',
        '</div>',

        // ---- Recent Changes ----
        '<div class="card">',
        '  <div class="card-header"><i class="bi bi-clock-history me-2"></i>RECENT CHANGES</div>',
        '  <div class="card-body p-0">',
        '    <div class="table-responsive">',
        '      <table class="table table-sm mb-0">',
        '        <thead><tr><th>TIMESTAMP</th><th>USER</th><th>ACTION</th><th>AFFECTED OBJECT</th></tr></thead>',
        '        <tbody id="audit-recent-tbody">',
        '          <tr><td colspan="4" class="text-center text-muted py-3">Loading...</td></tr>',
        '        </tbody>',
        '      </table>',
        '    </div>',
        '  </div>',
        '</div>'
    ].join('\n');
}

async function loadAudit() {
    var body = document.getElementById('section-body');
    if (body) body.innerHTML = _buildAuditScaffold();

    showLoading(true);
    try {
        var data = await apiFetch('/api/audit');
        renderAudit(data);
    } catch (e) {
        console.error('Audit load error:', e);
    }
    showLoading(false);
}

function renderAudit(data) {
    // ---- 사용자별 변경 횟수 ----
    var userHtml = data.by_user.length === 0
        ? '<tr><td colspan="2" class="text-center text-muted py-3">No data</td></tr>'
        : data.by_user.map(function (u) {
            return '<tr>' +
                '<td><i class="bi bi-person me-1"></i>' + escHtml(u.user) + '</td>' +
                '<td class="text-end"><span class="sev sev-info">' + u.count + '</span></td>' +
                '</tr>';
          }).join('');
    setEl('audit-user-tbody', userHtml, true);

    // ---- Recent Changes ----
    var recentHtml = data.recent.length === 0
        ? '<tr><td colspan="4" class="text-center text-muted py-3">No recent changes</td></tr>'
        : data.recent.map(function (r) {
            return '<tr>' +
                '<td><code>' + escHtml(r.timestamp) + '</code></td>' +
                '<td>' + escHtml(r.user) + '</td>' +
                '<td>' + actionBadge(r.action) + '</td>' +
                '<td style="max-width:250px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap"' +
                ' title="' + escHtml(r.affected) + '">' + escHtml(r.affected) + '</td>' +
                '</tr>';
          }).join('');
    setEl('audit-recent-tbody', recentHtml, true);
}