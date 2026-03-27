// ============================================================
// audit.js — Audit Log 섹션
// 의존: common.js (apiFetch, setEl, escHtml, actionBadge,
//                  showLoading)
// ============================================================

async function loadAudit() {
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

    // ---- Recent Changes 목록 ----
    var recentHtml = '';
    if (data.recent.length === 0) {
        recentHtml = '<tr><td colspan="4" class="text-center text-muted py-3">No recent changes</td></tr>';
    } else {
        recentHtml = data.recent.map(function (r) {
            return '<tr>' +
                '<td><code>' + escHtml(r.timestamp) + '</code></td>' +
                '<td>' + escHtml(r.user) + '</td>' +
                '<td>' + actionBadge(r.action) + '</td>' +
                '<td style="max-width:250px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap"' +
                ' title="' + escHtml(r.affected) + '">' + escHtml(r.affected) + '</td>' +
                '</tr>';
        }).join('');
    }
    setEl('audit-recent-tbody', recentHtml, true);
}