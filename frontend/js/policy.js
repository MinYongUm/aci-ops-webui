// ============================================================
// policy.js — Policy Check 섹션
// 버전: v1.8.0 — scaffold inject 방식으로 변경
// 의존: common.js (apiFetch, setEl, escHtml, miniStatCard,
//                  showLoading)
// ============================================================

function _buildPolicyScaffold() {
    return [
        // ---- 요약 ----
        '<div class="card mb-4">',
        '  <div class="card-header"><i class="bi bi-shield-lock-fill me-2"></i>POLICY SUMMARY</div>',
        '  <div class="card-body" id="policy-summary-content">',
        '    <div class="text-muted text-center py-3">Loading...</div>',
        '  </div>',
        '</div>',

        // ---- Risky Contracts ----
        '<div class="card mb-4">',
        '  <div class="card-header"><i class="bi bi-exclamation-triangle me-2"></i>RISKY CONTRACTS</div>',
        '  <div class="card-body p-0">',
        '    <div class="table-responsive">',
        '      <table class="table table-sm mb-0">',
        '        <thead><tr><th>TENANT</th><th>CONTRACT NAME</th></tr></thead>',
        '        <tbody id="policy-contracts-tbody">',
        '          <tr><td colspan="2" class="text-center text-muted py-3">Loading...</td></tr>',
        '        </tbody>',
        '      </table>',
        '    </div>',
        '  </div>',
        '</div>',

        // ---- Risky Filters ----
        '<div class="card">',
        '  <div class="card-header"><i class="bi bi-funnel me-2"></i>RISKY FILTERS</div>',
        '  <div class="card-body p-0">',
        '    <div class="table-responsive">',
        '      <table class="table table-sm mb-0">',
        '        <thead><tr><th>TENANT</th><th>FILTER NAME</th></tr></thead>',
        '        <tbody id="policy-filters-tbody">',
        '          <tr><td colspan="2" class="text-center text-muted py-3">Loading...</td></tr>',
        '        </tbody>',
        '      </table>',
        '    </div>',
        '  </div>',
        '</div>'
    ].join('\n');
}

async function loadPolicy() {
    var body = document.getElementById('section-body');
    if (body) body.innerHTML = _buildPolicyScaffold();

    showLoading(true);
    try {
        var data = await apiFetch('/api/policy');
        renderPolicy(data);
    } catch (e) {
        console.error('Policy load error:', e);
    }
    showLoading(false);
}

function renderPolicy(data) {
    // ---- Policy 요약 ----
    var riskBox = data.security_risks === 0
        ? '<div class="ok-box"><i class="bi bi-shield-check me-1"></i>No risky policies detected</div>'
        : '<div class="warn-box"><i class="bi bi-exclamation-triangle me-1"></i>' +
          data.security_risks + ' security risk(s) found</div>';

    var summaryHtml =
        '<div class="row g-2 mb-3">' +
        miniStatCard('Tenants',   data.total_tenants)  +
        miniStatCard('Contracts', data.total_contracts) +
        miniStatCard('Filters',   data.total_filters)   +
        miniStatCard('Risks',     data.security_risks,
            data.security_risks > 0 ? 'state-warn' : '') +
        '</div>' + riskBox;
    setEl('policy-summary-content', summaryHtml, true);

    // ---- Risky Contracts ----
    var contractsHtml = data.risky_contracts.length === 0
        ? '<tr><td colspan="2" class="text-center text-muted py-3">None detected</td></tr>'
        : data.risky_contracts.map(function (c) {
            return '<tr>' +
                '<td><code>' + escHtml(c.tenant) + '</code></td>' +
                '<td><span class="sev sev-critical">' + escHtml(c.name) + '</span></td>' +
                '</tr>';
          }).join('');
    setEl('policy-contracts-tbody', contractsHtml, true);

    // ---- Risky Filters ----
    var filtersHtml = data.risky_filters.length === 0
        ? '<tr><td colspan="2" class="text-center text-muted py-3">None detected</td></tr>'
        : data.risky_filters.map(function (f) {
            return '<tr>' +
                '<td><code>' + escHtml(f.tenant) + '</code></td>' +
                '<td><span class="sev sev-major">' + escHtml(f.name) + '</span></td>' +
                '</tr>';
          }).join('');
    setEl('policy-filters-tbody', filtersHtml, true);
}