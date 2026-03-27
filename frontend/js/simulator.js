// ============================================================
// simulator.js — Microseg Simulator 섹션
// 버전: v1.8.0 — scaffold inject 방식으로 변경
// 의존: common.js (apiFetch, setEl, escHtml, showLoading,
//                  simTenants)
// ============================================================

function _buildSimulatorScaffold() {
    return [
        // ---- EPG 선택 영역 ----
        '<div class="card mb-4">',
        '  <div class="card-header"><i class="bi bi-bezier2 me-2"></i>TRAFFIC SIMULATION</div>',
        '  <div class="card-body">',
        '    <div class="row g-3 mb-3">',

        '      <div class="col-md-5">',
        '        <label class="form-label" style="font-size:0.78rem;font-weight:600;color:var(--text-muted)">SOURCE EPG</label>',
        '        <select class="form-select form-select-sm mb-2" id="sim-src-tenant"',
        '                onchange="loadSimEpgs(\'src\')">',
        '          <option value="">-- Select Tenant --</option>',
        '        </select>',
        '        <select class="form-select form-select-sm" id="sim-src-epg">',
        '          <option value="">-- Select EPG --</option>',
        '        </select>',
        '      </div>',

        '      <div class="col-md-2 d-flex align-items-end justify-content-center pb-1">',
        '        <i class="bi bi-arrow-right" style="font-size:1.4rem;color:var(--text-dim)"></i>',
        '      </div>',

        '      <div class="col-md-5">',
        '        <label class="form-label" style="font-size:0.78rem;font-weight:600;color:var(--text-muted)">DESTINATION EPG</label>',
        '        <select class="form-select form-select-sm mb-2" id="sim-dst-tenant"',
        '                onchange="loadSimEpgs(\'dst\')">',
        '          <option value="">-- Select Tenant --</option>',
        '        </select>',
        '        <select class="form-select form-select-sm" id="sim-dst-epg">',
        '          <option value="">-- Select EPG --</option>',
        '        </select>',
        '      </div>',
        '    </div>',

        '    <button class="btn btn-cisco btn-sm" onclick="runSimulate()">',
        '      <i class="bi bi-play-fill me-1"></i>Simulate',
        '    </button>',
        '  </div>',
        '</div>',

        // ---- 판정 결과 (초기 hidden) ----
        '<div id="sim-verdict-area" style="display:none">',
        '  <div class="card mb-4">',
        '    <div class="card-header"><i class="bi bi-shield-check me-2"></i>SIMULATION RESULT</div>',
        '    <div class="card-body" id="sim-verdict-content"></div>',
        '  </div>',

        '  <div class="card" id="sim-contracts-card" style="display:none">',
        '    <div class="card-header"><i class="bi bi-file-earmark-text me-2"></i>MATCHED CONTRACTS</div>',
        '    <div class="card-body p-0">',
        '      <div class="table-responsive">',
        '        <table class="table table-sm mb-0">',
        '          <thead>',
        '            <tr><th>CONTRACT</th><th>TENANT</th><th>SUBJECTS</th><th>FILTERS</th></tr>',
        '          </thead>',
        '          <tbody id="sim-contracts-tbody"></tbody>',
        '        </table>',
        '      </div>',
        '    </div>',
        '  </div>',
        '</div>'
    ].join('\n');
}

async function loadSimulatorTenants() {
    var body = document.getElementById('section-body');
    if (body) body.innerHTML = _buildSimulatorScaffold();

    if (simTenants.length > 0) { renderSimTenants(); return; }
    try {
        simTenants = await apiFetch('/api/simulate/tenants');
        renderSimTenants();
    } catch (e) {
        console.error('Simulator tenants error:', e);
    }
}

async function loadSimEpgs(side) {
    var tenantEl = document.getElementById('sim-' + side + '-tenant');
    var epgEl    = document.getElementById('sim-' + side + '-epg');
    if (!tenantEl || !epgEl) return;

    var tenant = tenantEl.value;
    epgEl.innerHTML = '<option value="">-- Loading... --</option>';
    if (!tenant) { epgEl.innerHTML = '<option value="">-- Select EPG --</option>'; return; }

    try {
        var epgs = await apiFetch('/api/simulate/epgs?tenant=' + encodeURIComponent(tenant));
        epgEl.innerHTML = '<option value="">-- Select EPG --</option>';
        epgs.forEach(function (ep) {
            var opt = document.createElement('option');
            opt.value       = ep.dn;
            opt.textContent = ep.app_profile + ' / ' + ep.name;
            epgEl.appendChild(opt);
        });
    } catch (e) {
        epgEl.innerHTML = '<option value="">-- Error --</option>';
    }
}

async function runSimulate() {
    var srcDn = document.getElementById('sim-src-epg').value;
    var dstDn = document.getElementById('sim-dst-epg').value;

    if (!srcDn || !dstDn) {
        alert('Source EPG와 Destination EPG를 모두 선택하세요.');
        return;
    }

    showLoading(true);
    try {
        var result = await apiFetch('/api/simulate', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ src_epg_dn: srcDn, dst_epg_dn: dstDn })
        });
        renderSimResult(result);
    } catch (e) {
        console.error('Simulate error:', e);
    }
    showLoading(false);
}

function renderSimTenants() {
    ['src', 'dst'].forEach(function (side) {
        var sel = document.getElementById('sim-' + side + '-tenant');
        if (!sel) return;
        sel.innerHTML = '<option value="">-- Select Tenant --</option>';
        simTenants.forEach(function (t) {
            var name = typeof t === 'string' ? t : (t.name || t);
            var opt  = document.createElement('option');
            opt.value       = name;
            opt.textContent = name;
            sel.appendChild(opt);
        });
    });
}

function renderSimResult(result) {
    var area = document.getElementById('sim-verdict-area');
    if (area) area.style.display = 'block';

    var isAllow      = result.verdict === 'ALLOW';
    var iconClass    = isAllow ? 'bi-check-circle-fill' : 'bi-x-circle-fill';
    var color        = isAllow ? 'var(--color-success)' : 'var(--color-critical)';
    var boxClass     = isAllow ? 'sim-result-allow'     : 'sim-result-deny';

    var contentHtml =
        '<div class="mb-3">' + buildSimSvg(result, isAllow) + '</div>' +
        '<div class="' + boxClass + ' mb-3">' +
        '<i class="bi ' + iconClass + ' me-2" style="color:' + color + '"></i>' +
        '<strong style="color:' + color + '">' + result.verdict + '</strong>' +
        '</div>' +
        '<div style="font-size:0.85rem;color:var(--text-muted)">' +
        escHtml(result.reason || '') + '</div>';
    setEl('sim-verdict-content', contentHtml, true);

    // ---- Matched Contracts ----
    var contractsCard = document.getElementById('sim-contracts-card');
    if (isAllow && result.matched_contracts && result.matched_contracts.length > 0) {
        contractsCard.style.display = 'block';
        var contractsHtml = result.matched_contracts.map(function (c) {
            var subjects  = c.subjects || [];
            var subjNames = subjects.map(function (s) { return s.name; }).join(', ') || '-';
            var filters   = subjects
                .flatMap(function (s) { return (s.filters || []).map(function (f) { return f.name; }); })
                .join(', ') || '-';
            return '<tr>' +
                '<td><code>' + escHtml(c.name)    + '</code></td>' +
                '<td>'       + escHtml(c.tenant)  + '</td>'        +
                '<td>'       + escHtml(subjNames) + '</td>'        +
                '<td style="font-size:0.8rem;color:var(--text-muted)">' + escHtml(filters) + '</td>' +
                '</tr>';
        }).join('');
        setEl('sim-contracts-tbody', contractsHtml, true);
    } else {
        if (contractsCard) contractsCard.style.display = 'none';
    }
}

function buildSimSvg(result, isAllow) {
    var srcLabel  = (result.src_epg || '').split('/').pop() || 'SRC EPG';
    var dstLabel  = (result.dst_epg || '').split('/').pop() || 'DST EPG';
    var lineColor = isAllow ? '#22c55e' : '#ef4444';
    var midLabel  = isAllow ? 'ALLOW'   : 'DENY';
    var dashArray = isAllow ? 'none'    : '5,3';

    return '<svg viewBox="0 0 460 60" xmlns="http://www.w3.org/2000/svg"' +
        ' style="max-width:460px;width:100%">' +
        '<rect x="0"   y="10" width="130" height="36" rx="6" fill="none"' +
        ' stroke="var(--border-color)" stroke-width="1.5"/>' +
        '<text x="65"  y="32" text-anchor="middle" font-size="10"' +
        ' fill="var(--text-main)" font-family="monospace">' +
        escHtml(srcLabel.substring(0, 14)) + '</text>' +
        '<rect x="330" y="10" width="130" height="36" rx="6" fill="none"' +
        ' stroke="var(--border-color)" stroke-width="1.5"/>' +
        '<text x="395" y="32" text-anchor="middle" font-size="10"' +
        ' fill="var(--text-main)" font-family="monospace">' +
        escHtml(dstLabel.substring(0, 14)) + '</text>' +
        '<line x1="130" y1="28" x2="325" y2="28" stroke="' + lineColor + '"' +
        ' stroke-width="1.5" stroke-dasharray="' + dashArray + '"/>' +
        '<polygon points="320,23 330,28 320,33" fill="' + lineColor + '"/>' +
        '<text x="230" y="22" text-anchor="middle" font-size="10" font-weight="bold"' +
        ' fill="' + lineColor + '">' + midLabel + '</text>' +
        '</svg>';
}