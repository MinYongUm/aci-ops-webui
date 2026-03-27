// ============================================================
// settings.js — APIC 설정 관리
// 버전: v1.9.1
//
// 담당 섹션: Settings
// API:
//   GET  /api/setup/config  현재 설정 조회 (password 마스킹)
//   POST /api/setup/test    연결 테스트 (전체 호스트 per-host 결과 반환)
//   POST /api/setup/save    설정 저장 + ACIClient 재초기화
//
// password 처리 원칙:
//   - GET 응답의 "********"는 폼에 채우지 않음
//   - 저장 시 항상 재입력 필요
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
            // password는 마스킹값을 채우지 않음 — 재입력 유도
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
                '<div class="alert alert-warning">' +
                '<i class="bi bi-exclamation-triangle me-1"></i>' +
                '설정을 불러오지 못했습니다.</div>';
        }
    }

    showLoading(false);
}

// ============================================================
// VALIDATE — 공통 입력값 검증
// ============================================================
function _validateSettingsInput() {
    var hosts      = _settingsHosts.filter(function (h) { return h.trim(); });
    var usernameEl = document.getElementById('settings-username');
    var passwordEl = document.getElementById('settings-password');
    var resultEl   = document.getElementById('settings-result');

    var username = usernameEl ? usernameEl.value.trim() : '';
    var password = passwordEl ? passwordEl.value : '';

    if (hosts.length === 0) {
        if (resultEl) {
            resultEl.innerHTML =
                '<div class="alert alert-warning">' +
                '<i class="bi bi-exclamation-triangle me-1"></i>' +
                'APIC 주소를 1개 이상 입력하세요.</div>';
        }
        return null;
    }
    if (!username) {
        if (resultEl) {
            resultEl.innerHTML =
                '<div class="alert alert-warning">' +
                '<i class="bi bi-exclamation-triangle me-1"></i>' +
                'Username을 입력하세요.</div>';
        }
        return null;
    }
    if (!password) {
        if (resultEl) {
            resultEl.innerHTML =
                '<div class="alert alert-warning">' +
                '<i class="bi bi-exclamation-triangle me-1"></i>' +
                'Password를 입력하세요.</div>';
        }
        return null;
    }

    return { hosts: hosts, username: username, password: password };
}

// ============================================================
// RENDER HOST RESULTS — per-host 연결 상태 표시
// ============================================================
function _renderHostResults(hostResults) {
    if (!hostResults || hostResults.length === 0) return '';

    var html = '<div class="mb-3">';
    hostResults.forEach(function (r) {
        if (r.ok) {
            html += '<div class="d-flex align-items-center gap-2 mb-1">' +
                '<i class="bi bi-check-circle-fill text-success"></i>' +
                '<span>' + escHtml(r.host) + '</span>' +
                '</div>';
        } else {
            html += '<div class="d-flex align-items-center gap-2 mb-1">' +
                '<i class="bi bi-x-circle-fill text-danger"></i>' +
                '<span style="color:var(--text-muted)">' + escHtml(r.host) + '</span>' +
                (r.reason
                    ? '<small class="text-danger">(' + escHtml(r.reason) + ')</small>'
                    : '') +
                '</div>';
        }
    });
    html += '</div>';
    return html;
}

// ============================================================
// TEST CONNECTION — POST /api/setup/test
// ============================================================
async function testSettingsConnection() {
    var resultEl = document.getElementById('settings-result');
    if (resultEl) resultEl.innerHTML = '';

    // 테스트 시작 시 Save 버튼 비활성화 (이전 성공 결과 무효화)
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

        // per-host 결과 + 전체 요약 메시지 렌더링
        var html = _renderHostResults(result.host_results);

        if (result.success) {
            html += '<div class="alert alert-success mb-0">' +
                '<i class="bi bi-check-circle me-1"></i>' +
                escHtml(result.message) + '</div>';
            if (resultEl) resultEl.innerHTML = html;
            if (saveBtn) saveBtn.disabled = false;
        } else {
            html += '<div class="alert alert-danger mb-0">' +
                '<i class="bi bi-x-circle me-1"></i>' +
                escHtml(result.message) + '</div>';
            if (resultEl) resultEl.innerHTML = html;
        }

    } catch (e) {
        if (resultEl) {
            resultEl.innerHTML =
                '<div class="alert alert-danger">' +
                '<i class="bi bi-x-circle me-1"></i>' +
                '연결 테스트 중 오류가 발생했습니다.</div>';
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

            // Save 버튼 비활성 유지 — 재테스트 유도
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = '<i class="bi bi-floppy me-1"></i>Save';
            }

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
                '<div class="alert alert-danger">' +
                '<i class="bi bi-x-circle me-1"></i>' +
                '저장 중 오류가 발생했습니다.</div>';
        }
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-floppy me-1"></i>Save';
        }
    }
}