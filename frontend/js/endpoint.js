// ============================================================
// endpoint.js — Endpoint Tracker 섹션
// 버전: v1.8.0 — scaffold inject 방식으로 변경
// 의존: common.js (apiFetch, setEl, escHtml, showLoading)
// ============================================================

function _buildEndpointScaffold() {
    return [
        // ---- 검색 ----
        '<div class="card mb-4">',
        '  <div class="card-header"><i class="bi bi-search me-2"></i>ENDPOINT SEARCH</div>',
        '  <div class="card-body">',
        '    <div class="d-flex gap-2 mb-3">',
        '      <input type="text" class="form-control" id="ep-search-input"',
        '             placeholder="MAC (00:50:56:xx:xx:xx) 또는 IP (10.0.0.1)"',
        '             onkeypress="if(event.key===\'Enter\')searchEndpoint()">',
        '      <button class="btn btn-cisco btn-sm" onclick="searchEndpoint()" style="white-space:nowrap">',
        '        <i class="bi bi-search me-1"></i>Search',
        '      </button>',
        '    </div>',
        '    <div id="ep-search-results"></div>',
        '  </div>',
        '</div>',

        // ---- Tenant별 통계 ----
        '<div class="card">',
        '  <div class="card-header"><i class="bi bi-hdd-network-fill me-2"></i>ENDPOINTS BY TENANT</div>',
        '  <div class="card-body p-0">',
        '    <div class="table-responsive">',
        '      <table class="table table-sm mb-0">',
        '        <thead><tr><th>TENANT</th><th class="text-end">COUNT</th></tr></thead>',
        '        <tbody id="ep-tenant-tbody">',
        '          <tr><td colspan="2" class="text-center text-muted py-3">Loading...</td></tr>',
        '        </tbody>',
        '      </table>',
        '    </div>',
        '  </div>',
        '</div>'
    ].join('\n');
}

async function loadEndpoint() {
    var body = document.getElementById('section-body');
    if (body) body.innerHTML = _buildEndpointScaffold();

    showLoading(true);
    try {
        var data = await apiFetch('/api/endpoint');
        renderEndpoint(data);
    } catch (e) {
        console.error('Endpoint load error:', e);
    }
    showLoading(false);
}

function renderEndpoint(data) {
    var tenantHtml = data.by_tenant.length === 0
        ? '<tr><td colspan="2" class="text-center text-muted py-3">No endpoints</td></tr>'
        : data.by_tenant.map(function (t) {
            return '<tr>' +
                '<td>' + escHtml(t.tenant) + '</td>' +
                '<td class="text-end"><span class="sev sev-info">' + t.count + '</span></td>' +
                '</tr>';
          }).join('');
    setEl('ep-tenant-tbody', tenantHtml, true);
}

async function searchEndpoint() {
    var inputEl = document.getElementById('ep-search-input');
    if (!inputEl) return;
    var q = inputEl.value.trim();
    if (!q) { alert('MAC 또는 IP 주소를 입력하세요.'); return; }

    var resultEl = document.getElementById('ep-search-results');
    resultEl.innerHTML = '<div class="info-box">Searching...</div>';

    try {
        var results = await apiFetch('/api/endpoint/search?q=' + encodeURIComponent(q));
        renderEndpointSearch(results, resultEl);
    } catch (e) {
        resultEl.innerHTML = '<div class="critical-box">Search error: ' + e.message + '</div>';
    }
}

function renderEndpointSearch(results, el) {
    if (results.length === 0) {
        el.innerHTML = '<div class="warn-box">No endpoints found matching the query.</div>';
        return;
    }

    var rows = results.map(function (ep) {
        return '<tr>' +
            '<td><code>' + escHtml(ep.mac)       + '</code></td>' +
            '<td><code>' + escHtml(ep.ip)         + '</code></td>' +
            '<td>'       + escHtml(ep.tenant)     + '</td>'        +
            '<td>'       + escHtml(ep.epg)        + '</td>'        +
            '<td><span class="sev sev-info">Node ' + escHtml(ep.node) + '</span></td>' +
            '<td><code>' + escHtml(ep.interface)  + '</code></td>' +
            '</tr>';
    }).join('');

    el.innerHTML =
        '<div class="info-box mb-2">' + results.length + ' endpoint(s) found</div>' +
        '<div class="table-responsive">' +
        '<table class="table table-sm">' +
        '<thead><tr><th>MAC</th><th>IP</th><th>TENANT</th><th>EPG</th><th>NODE</th><th>INTERFACE</th></tr></thead>' +
        '<tbody>' + rows + '</tbody>' +
        '</table></div>';
}