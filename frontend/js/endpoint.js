// ============================================================
// endpoint.js — Endpoint Tracker 섹션
// 의존: common.js (apiFetch, setEl, escHtml, showLoading)
// ============================================================

async function loadEndpoint() {
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
    var q = document.getElementById('ep-search-input').value.trim();
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
            '<td><code>' + escHtml(ep.ip)        + '</code></td>' +
            '<td>'       + escHtml(ep.tenant)    + '</td>'        +
            '<td>'       + escHtml(ep.epg)       + '</td>'        +
            '<td><span class="sev sev-info">Node ' + escHtml(ep.node)      + '</span></td>' +
            '<td><code>' + escHtml(ep.interface) + '</code></td>' +
            '</tr>';
    }).join('');

    el.innerHTML =
        '<div class="info-box mb-2">' + results.length + ' endpoint(s) found</div>' +
        '<div class="table-responsive">' +
        '<table class="table">' +
        '<thead><tr><th>MAC</th><th>IP</th><th>Tenant</th><th>EPG</th><th>Node</th><th>Interface</th></tr></thead>' +
        '<tbody>' + rows + '</tbody>' +
        '</table></div>';
}