// ============================================================
// settings.js — APIC 설정 관리
// 버전: v1.9.1
// ============================================================

// ============================================================
// SCAFFOLD
// ============================================================
function _buildSettingsScaffold() {
    return '<div class="row g-4">' +
        '<div class="col-12 col-lg-8 col-xl-6">' +
        '<div class="panel">' +
        '<div class="panel-header">APIC Connection Settings</div>' +
        '<div class="panel-body">' +

        // APIC Hosts
        '<div class="mb-4">' +
        '<label class="form-label fw-semibold">APIC Hosts</label>' +
        '<div id="settings-hosts-list"></div>' +
        '<button class="btn btn-sm btn-outline-secondary mt-2" onclick="addSettingsHost()">' +
        '<i class="bi bi-plus-circle me-1"></i>Add Host</button>' +
        '</div>' +

        // Username
        '<div class="mb-3">' +
        '<label class="form-label fw-semibold">Username</label>' +
        '<input type="text" class="form-control" id="settings-username" placeholder="admin">' +
        '</div>' +

        // Password
        '<div class="mb-4">' +
        '<label class="form-label fw-semibold">Password</label>' +
        '<input type="password" class="form-control" id="settings-password" ' +
        'placeholder="보안상 비밀번호를 다시 입력하세요">' +
        '<div class="form-text">저장 시 현재 비밀번호를 반드시 입력해야 합니다.</div>' +
        '</div>' +

        // Result
        '<div id="settings-result" class="mb-3"></div>' +

        // Buttons
        '<div class="d-flex gap-2">' +
        '<button class="btn btn-cisco" onclick="testSettingsConnection()" id="btn-settings-test">' +
        '<i class="bi bi-wifi me-1"></i>Test Connection</button>' +
        '<button class="btn btn-success" onclick="saveSettings()" ' +
        'id="btn-settings-save" disabled>' +
        '<i class="bi bi-floppy me-1"></i>Save</button>' +
        '</div>' +

        '</div></div></div></div>';
}

// ============================================================
// HOST LIST 관리
// ============================================================
var _settingsHosts = [];

function _renderSettingsHosts() {
    var list = document.getElementById('settings-hosts-list');
    if (!list) return;

    if (_settingsHosts.length === 0) {
        _settingsHosts = [''];
    }

    var html = '';
    _settingsHosts.forEach(function (host, idx) {
        html += '<div class="input-group mb-2">' +
            '<input type="text" class="form-control" ' +
            'value="' + escHtml(host) + '" ' +
            'placeholder="https://APIC_IP_OR_HOSTNAME" ' +
            'oninput="_settingsHosts[' + idx + '] = this.value">' +
            (_settingsHosts.length > 1
                ? '<button class="btn btn-outline-danger" ' +
                  'onclick="removeSettingsHost(' + idx + ')">' +
                  '<i class="bi bi-trash"></i></button>'
                : '') +
            '</div>';
    });

    list.innerHTML = html;
}

function addSettingsHost() {
    _settingsHosts.push('');
    _renderSettingsHosts();
}

function removeSettingsHost(idx) {
    _settingsHosts.splice(idx, 1);
    _renderSettingsHosts();
}

// ============================================================
// LOAD — GET /api/setup/config
// ============================================================
async function loadSettings() {
    var body = document.getElementById('section-body');
    if (body) body.innerHTML = _buildSettingsScaffold();

    showLoading(true);

    try {
        var data = await apiFetch('/api/setup/config');

        if (data.configured) {
            _settingsHosts = data.hosts.length > 0 ? data.hosts.slice() : [''];
            var usernameEl = document.getElementById('settings-username');
            if (usernameEl) usernameEl.value = data.username;
        } else {
            _settingsHosts = [''];
        }

        _renderSettingsHosts();

    } catch (e) {
        _settingsHosts = [''];
        _renderSettingsHosts();
        var resultEl = document.getElementById('settings-result');
        if (resultEl) {
            resultEl.innerHTML =
                '<div class="alert alert-warning">설정을 불러오지 못했습니다.</div>';
        }
    }

    showLoading(false);
}

// ============================================================
// VALIDATE — 공통 입력값 검증
// ============================================================
function _validateSettingsInput() {
    var hosts    = _settingsHosts.filter(function (h) { return h.trim(); });
    var username = document.getElementById('settings-username').value.trim();
    var password = document.getElementById('settings-password').value;
    var resultEl = document.getElementById('settings-result');

    if (hosts.length === 0) {
        if (resultEl) {
            resultEl.innerHTML =
                '<div class="alert alert-warning">APIC 주소를 1개 이상 입력하세요.</div>';
        }
        return null;
    }
    if (!username) {
        if (resultEl) {
            resultEl.innerHTML =
                '<div class="alert alert-warning">Username을 입력하세요.</div>';
        }
        return null;
    }
    if (!password) {
        if (resultEl) {
            resultEl.innerHTML =
                '<div class="alert alert-warning">Password를 입력하세요.</div>';
        }
        return null;
    }

    return { hosts: hosts, username: username, password: password };
}

// ============================================================
// TEST CONNECTION — POST /api/setup/test
// ============================================================
async function testSettingsConnection() {
    var resultEl = document.getElementById('settings-result');
    if (resultEl) resultEl.innerHTML = '';

    var saveBtn = document.getElementById('btn-settings-save');
    if (saveBtn) saveBtn.disabled = true;

    var payload = _validateSettingsInput();
    if (!payload) return;

    var btn = document.getElementById('btn-settings-test');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML =
            '<span class="spinner-border spinner-border-sm me-1"></span>Testing...';
    }

    try {
        var result = await apiFetch('/api/setup/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (result.success) {
            if (resultEl) {
                resultEl.innerHTML =
                    '<div class="alert alert-success">' +
                    '<i class="bi bi-check-circle me-1"></i>' +
                    escHtml(result.message) + '</div>';
            }
            if (saveBtn) saveBtn.disabled = false;
        } else {
            if (resultEl) {
                resultEl.innerHTML =
                    '<div class="alert alert-danger">' +
                    '<i class="bi bi-x-circle me-1"></i>' +
                    escHtml(result.message) + '</div>';
            }
        }

    } catch (e) {
        if (resultEl) {
            resultEl.innerHTML =
                '<div class="alert alert-danger">연결 테스트 중 오류가 발생했습니다.</div>';
        }
    }

    if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-wifi me-1"></i>Test Connection';
    }
}

// ============================================================
// SAVE — POST /api/setup/save
// ============================================================
async function saveSettings() {
    var resultEl = document.getElementById('settings-result');
    if (resultEl) resultEl.innerHTML = '';

    var payload = _validateSettingsInput();
    if (!payload) return;

    var btn = document.getElementById('btn-settings-save');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML =
            '<span class="spinner-border spinner-border-sm me-1"></span>Saving...';
    }

    try {
        var result = await apiFetch('/api/setup/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (result.success) {
            if (resultEl) {
                resultEl.innerHTML =
                    '<div class="alert alert-success">' +
                    '<i class="bi bi-check-circle me-1"></i>' +
                    escHtml(result.message) + '</div>';
            }
            // 대시보드 유지 — 페이지 이동 없음
            // password 필드 초기화 (저장 완료 후 재입력 유도)
            var pwEl = document.getElementById('settings-password');
            if (pwEl) pwEl.value = '';

        } else {
            if (resultEl) {
                resultEl.innerHTML =
                    '<div class="alert alert-danger">' +
                    '<i class="bi bi-x-circle me-1"></i>' +
                    escHtml(result.message) + '</div>';
            }
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<i class="bi bi-floppy me-1"></i>Save';
            }
        }

    } catch (e) {
        if (resultEl) {
            resultEl.innerHTML =
                '<div class="alert alert-danger">저장 중 오류가 발생했습니다.</div>';
        }
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-floppy me-1"></i>Save';
        }
    }
}