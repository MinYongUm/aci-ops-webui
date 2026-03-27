// ============================================================
// topology.js — Topology Viewer 섹션
// 버전: v1.8.0 — scaffold inject 방식으로 변경
// 의존: common.js (apiFetch, setEl, escHtml, showLoading)
// ============================================================

function _buildTopologyScaffold() {
    return [
        // ---- 다이어그램 ----
        '<div class="card mb-4">',
        '  <div class="card-header">',
        '    <i class="bi bi-diagram-3 me-2"></i>FABRIC TOPOLOGY',
        '    <span class="ms-2" style="font-size:0.78rem;font-weight:400;color:var(--text-muted)"',
        '          id="topo-summary"></span>',
        '  </div>',
        '  <div class="card-body">',
        '    <div id="topo-content" class="topology-container">',
        '      <div class="text-muted text-center py-3">Loading...</div>',
        '    </div>',
        '  </div>',
        '</div>',

        // ---- Node Details ----
        '<div class="card">',
        '  <div class="card-header"><i class="bi bi-server me-2"></i>NODE DETAILS</div>',
        '  <div class="card-body p-0">',
        '    <div class="table-responsive">',
        '      <table class="table table-sm mb-0">',
        '        <thead>',
        '          <tr><th>ROLE</th><th>ID</th><th>NAME</th><th>MODEL</th><th>STATUS</th></tr>',
        '        </thead>',
        '        <tbody id="topo-table-tbody">',
        '          <tr><td colspan="5" class="text-center text-muted py-3">Loading...</td></tr>',
        '        </tbody>',
        '      </table>',
        '    </div>',
        '  </div>',
        '</div>'
    ].join('\n');
}

async function loadTopology() {
    var body = document.getElementById('section-body');
    if (body) body.innerHTML = _buildTopologyScaffold();

    showLoading(true);
    try {
        var data = await apiFetch('/api/topology');
        renderTopology(data);
    } catch (e) {
        console.error('Topology load error:', e);
    }
    showLoading(false);
}

function renderTopology(data) {
    // ---- 요약 레이블 ----
    setEl('topo-summary',
        data.summary.controllers + 'C / ' +
        data.summary.spines      + 'S / ' +
        data.summary.leafs       + 'L');

    // ---- 토폴로지 다이어그램 ----
    var topoHtml =
        _topoLayer('Controllers', data.controllers, false) +
        '<div class="connector-line"></div>' +
        _topoLayer('Spines',      data.spines,      false) +
        '<div class="connector-line"></div>' +
        _topoLayer('Leafs',       data.leafs,       true);
    setEl('topo-content', topoHtml, true);

    // ---- Node Details 테이블 ----
    var allNodes = [].concat(
        data.controllers.map(function (n) { return Object.assign({}, n, { role: 'Controller' }); }),
        data.spines.map(function (n)      { return Object.assign({}, n, { role: 'Spine' }); }),
        data.leafs.map(function (n)       { return Object.assign({}, n, { role: 'Leaf' }); })
    );

    var tableHtml = allNodes.map(function (n) {
        var roleSev = n.role === 'Controller' ? 'sev-warning' :
                      n.role === 'Spine'       ? 'sev-info'    : 'sev-minor';
        var stSev   = n.status === 'UP' ? 'sev-minor' : 'sev-critical';
        return '<tr>' +
            '<td><span class="sev ' + roleSev + '">' + n.role + '</span></td>' +
            '<td><code>' + n.id + '</code></td>' +
            '<td>' + n.name + '</td>' +
            '<td style="color:var(--text-muted);font-size:0.8rem">' + (n.model || '-') + '</td>' +
            '<td><span class="sev ' + stSev + '">' + n.status + '</span></td>' +
            '</tr>';
    }).join('');

    setEl('topo-table-tbody',
        tableHtml || '<tr><td colspan="5" class="text-muted text-center py-3">No nodes</td></tr>',
        true);
}

// ---- 내부 헬퍼: 레이어 한 줄 생성 ----
function _topoLayer(label, nodes, isLeaf) {
    var chips = nodes.map(function (n) {
        var borderStyle = (isLeaf && n.status !== 'UP')
            ? ' style="border-color:var(--color-critical)"' : '';
        return '<div class="node-chip"' + borderStyle + '>' +
            '<div class="status-dot ' + (n.status === 'UP' ? 'dot-up' : 'dot-down') + '"></div>' +
            n.name +
            '</div>';
    }).join('');

    return '<div class="layer-label">' + label + '</div>' +
           '<div style="text-align:center;margin-bottom:4px">' + chips + '</div>';
}