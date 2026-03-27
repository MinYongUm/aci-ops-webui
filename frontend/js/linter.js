// ============================================================
// linter.js — Config Linter 섹션
// 의존: common.js (apiFetch, setEl, escHtml, showLoading)
// ============================================================

async function runLinterLive() {
    var statusEl = document.getElementById('linter-status');
    statusEl.textContent = 'Scanning...';
    showLoading(true);
    try {
        var data = await apiFetch('/api/lint');
        renderLinter(data, 'live');
        statusEl.textContent = 'Live scan completed — ' + new Date().toLocaleTimeString();
    } catch (e) {
        statusEl.textContent = 'Error: ' + e.message;
    }
    showLoading(false);
}

async function uploadLinter() {
    var fileInput = document.getElementById('linter-file-input');
    if (!fileInput.files.length) return;

    var statusEl = document.getElementById('linter-status');
    statusEl.textContent = 'Analyzing ' + fileInput.files[0].name + '...';
    showLoading(true);

    var formData = new FormData();
    formData.append('file', fileInput.files[0]);

    try {
        var data = await apiFetch('/api/lint/upload', { method: 'POST', body: formData });
        renderLinter(data, 'upload');
        statusEl.textContent = 'Upload scan completed — ' + new Date().toLocaleTimeString();
    } catch (e) {
        statusEl.textContent = 'Error: ' + e.message;
    }
    showLoading(false);
    fileInput.value = '';  // 파일 선택 초기화
}

function renderLinter(data, source) {
    var area = document.getElementById('linter-result-area');
    area.style.display = 'block';

    var srcLabel   = source === 'live' ? 'Live Scan (APIC)' : 'File Upload';
    var summaryHtml = data.total_issues === 0
        ? '<div class="ok-box"><i class="bi bi-check-circle me-1"></i>' +
          srcLabel + ' — No issues found. Config looks clean.</div>'
        : '<div class="' + (data.summary.critical > 0 ? 'critical-box' : 'warn-box') + '">' +
          '<i class="bi bi-exclamation-triangle me-1"></i>' +
          srcLabel + ' — ' + data.total_issues + ' issue(s) found: ' +
          '<strong>' + data.summary.critical + ' critical</strong>, ' +
          data.summary.warning + ' warning</div>';
    setEl('linter-summary-box', summaryHtml, true);

    if (data.results.length === 0) {
        setEl('linter-tbody',
            '<tr><td colspan="5" class="text-center text-muted py-3">No issues detected</td></tr>',
            true);
        return;
    }

    var tbody = data.results.map(function (r) {
        var sevClass = r.severity === 'critical' ? 'sev-critical' : 'sev-major';
        return '<tr>' +
            '<td><code>' + escHtml(r.rule_id) + '</code></td>' +
            '<td><span class="sev ' + sevClass + '">' + escHtml(r.severity) + '</span></td>' +
            '<td><span class="sev sev-info">'  + escHtml(r.category) + '</span></td>' +
            '<td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;' +
            'font-family:var(--font-mono);font-size:14px" title="' + escHtml(r.dn) + '">' +
            escHtml(r.dn) + '</td>' +
            '<td style="font-size:15px">' + escHtml(r.message) + '</td>' +
            '</tr>';
    }).join('');
    setEl('linter-tbody', tbody, true);
}