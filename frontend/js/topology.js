// ============================================================
// topology.js — Topology Viewer 섹션
// 의존: common.js (apiFetch, setEl, escHtml, showLoading)
// ============================================================

async function loadTopology() {
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
    document.getElementById('topo-summary').textContent =
        data.summary.controllers + 'C / ' +
        data.summary.spines      + 'S / ' +
        data.summary.leafs       + 'L';

    // ---- 토폴로지 다이어그램 ----
    var topoHtml =
        _topoLayer('Controllers', data.controllers, false) +
        '<div class="topo-line"></div>' +
        _topoLayer('Spines',      data.spines,      false) +
        '<div class="topo-line"></div>' +
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
            '<td style="color:var(--text-muted);font-size:14px">' + (n.model || '-') + '</td>' +
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
            '<div class="dot ' + (n.status === 'UP' ? 'dot-up' : 'dot-down') + '"></div>' +
            n.name +
            '</div>';
    }).join('');

    return '<div class="topo-layer">' +
        '<div class="topo-label">' + label + '</div>' +
        '<div class="topo-nodes">' + chips + '</div>' +
        '</div>';
}