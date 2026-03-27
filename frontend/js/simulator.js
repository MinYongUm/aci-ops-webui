// ============================================================
// simulator.js — Microseg Simulator 섹션
// 의존: common.js (apiFetch, setEl, escHtml, showLoading,
//                  simTenants)
// ============================================================

async function loadSimulatorTenants() {
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
    var tenant   = tenantEl.value;

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

// ---- Tenant 드롭다운 렌더링 ----
function renderSimTenants() {
    ['src', 'dst'].forEach(function (side) {
        var sel = document.getElementById('sim-' + side + '-tenant');
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

// ---- 판정 결과 렌더링 ----
function renderSimResult(result) {
    var area = document.getElementById('sim-verdict-area');
    area.style.display = 'block';

    var isAllow      = result.verdict === 'ALLOW';
    var verdictClass = isAllow ? 'verdict-allow' : 'verdict-deny';
    var iconClass    = isAllow ? 'bi-check-circle-fill' : 'bi-x-circle-fill';
    var color        = isAllow ? 'var(--color-success)' : 'var(--color-critical)';

    var contentHtml =
        '<div class="mb-3">' + buildSimSvg(result, isAllow) + '</div>' +
        '<div class="verdict-box ' + verdictClass + ' mb-2">' +
        '<i class="bi ' + iconClass + ' me-2" style="color:' + color + '"></i>' +
        '<span class="verdict-label" style="color:' + color + '">' + result.verdict + '</span>' +
        '</div>' +
        '<div style="font-size:15px;color:var(--text-muted)">' + escHtml(result.reason || '') + '</div>';
    setEl('sim-verdict-content', contentHtml, true);

    // ---- Matched Contracts 테이블 ----
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
                '<td><code>' + escHtml(c.name)   + '</code></td>' +
                '<td>'       + escHtml(c.tenant)  + '</td>'        +
                '<td>'       + escHtml(subjNames) + '</td>'        +
                '<td style="font-size:14px;color:var(--text-muted)">' + escHtml(filters) + '</td>' +
                '</tr>';
        }).join('');
        setEl('sim-contracts-tbody', contractsHtml, true);
    } else {
        contractsCard.style.display = 'none';
    }
}

// ---- SVG 흐름도 ----
function buildSimSvg(result, isAllow) {
    var srcLabel = (result.src_epg || '').split('/').pop() || 'SRC EPG';
    var dstLabel = (result.dst_epg || '').split('/').pop() || 'DST EPG';
    var lineColor = isAllow ? '#3fb950' : '#f85149';
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
        '<line x1="130" y1="28" x2="330" y2="28" stroke="' + lineColor + '"' +
        ' stroke-width="1.5" stroke-dasharray="' + dashArray + '"/>' +
        '<polygon points="325,23 335,28 325,33" fill="' + lineColor + '"/>' +
        '<text x="230" y="22" text-anchor="middle" font-size="10" font-weight="bold"' +
        ' fill="' + lineColor + '">' + midLabel + '</text>' +
        '</svg>';
}