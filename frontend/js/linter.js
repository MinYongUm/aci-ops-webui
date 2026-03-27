// ============================================================
// linter.js — Config Linter 섹션
// 버전: v1.8.0 — scaffold inject 방식으로 변경 (수동 트리거 유지)
// 의존: common.js (apiFetch, setEl, escHtml, showLoading)
// ============================================================

function _buildLinterScaffold() {
    return [
        // ---- 컨트롤 영역 ----
        '<div class="card mb-4">',
        '  <div class="card-header"><i class="bi bi-file-code-fill me-2"></i>CONFIG LINTER</div>',
        '  <div class="card-body">',
        '    <div class="d-flex flex-wrap gap-3 align-items-center mb-3">',
        '      <button class="btn btn-cisco btn-sm" onclick="runLinterLive()">',
        '        <i class="bi bi-lightning-charge me-1"></i>Live Scan (APIC)',
        '      </button>',
        '      <div class="d-flex gap-2 align-items-center">',
        '        <input type="file" class="form-control form-control-sm" id="linter-file-input"',
        '               accept=".json" style="max-width:240px">',
        '        <button class="btn btn-outline-cisco btn-sm" onclick="uploadLinter()">',
        '          <i class="bi bi-upload me-1"></i>Analyze File',
        '        </button>',
        '      </div>',
        '    </div>',
        '    <div id="linter-status" style="font-size:0.8rem;color:var(--text-muted)">',
        '      Scan 버튼을 눌러 분석을 시작하세요.',
        '    </div>',
        '  </div>',
        '</div>',

        // ---- 결과 영역 (초기 hidden) ----
        '<div id="linter-result-area" style="display:none">',
        '  <div id="linter-summary-box" class="mb-4"></div>',
        '  <div class="card">',
        '    <div class="card-header"><i class="bi bi-list-ul me-2"></i>ISSUES</div>',
        '    <div class="card-body p-0">',
        '      <div class="table-responsive">',
        '        <table class="table table-sm mb-0">',
        '          <thead>',
        '            <tr>',
        '              <th style="width:90px">RULE</th>',
        '              <th style="width:80px">SEVERITY</th>',
        '              <th style="width:90px">CATEGORY</th>',
        '              <th>DN</th>',
        '              <th>MESSAGE</th>',
        '            </tr>',
        '          </thead>',
        '          <tbody id="linter-tbody">',
        '            <tr><td colspan="5" class="text-center text-muted py-3">No results yet</td></tr>',
        '          </tbody>',
        '        </table>',
        '      </div>',
        '    </div>',
        '  </div>',
        '</div>'
    ].join('\n');
}

// loadSection('linter')은 common.js에서 return; (수동 트리거만)
// 사이드바 클릭 시 scaffold만 inject, 스캔은 버튼으로 실행
function loadLinter() {
    var body = document.getElementById('section-body');
    if (body) body.innerHTML = _buildLinterScaffold();
}

// common.js loadSection()의 linter case가 return이므로
// navigateTo('linter') 시 scaffold inject를 위해 common.js 패치
var _origLoadSection = window.loadSection;
window.loadSection = function(section) {
    if (section === 'linter') {
        loadLinter();
        return;
    }
    return _origLoadSection(section);
};

async function runLinterLive() {
    var statusEl = document.getElementById('linter-status');
    if (!statusEl) return;
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
    if (!fileInput || !fileInput.files.length) return;

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
    fileInput.value = '';
}

function renderLinter(data, source) {
    var area = document.getElementById('linter-result-area');
    if (area) area.style.display = 'block';

    var srcLabel    = source === 'live' ? 'Live Scan (APIC)' : 'File Upload';
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
            'font-family:monospace;font-size:0.8rem" title="' + escHtml(r.dn) + '">' +
            escHtml(r.dn) + '</td>' +
            '<td style="font-size:0.85rem">' + escHtml(r.message) + '</td>' +
            '</tr>';
    }).join('');
    setEl('linter-tbody', tbody, true);
}