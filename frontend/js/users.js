// ============================================================
// users.js — 사용자 관리 섹션 (admin 전용)
// 버전: v1.9.2
//
// 담당 섹션: Users
// API:
//   GET    /api/users                      사용자 목록
//   POST   /api/users                      사용자 생성
//   DELETE /api/users/{username}           사용자 삭제
//   PUT    /api/users/{username}/password  비밀번호 변경
// ============================================================

// ============================================================
// SCAFFOLD — settings.js와 동일한 Bootstrap + style.css 패턴 사용
// ============================================================
function _buildUsersScaffold() {
    return '<div class="row g-4">' +

        // 왼쪽: 사용자 생성 폼
        '<div class="col-12 col-lg-5">' +
        '<div class="panel">' +
        '<div class="panel-header">New User</div>' +
        '<div class="panel-body">' +

        '<div class="mb-3">' +
        '<label class="form-label fw-semibold">Username</label>' +
        '<input type="text" class="form-control" id="new-username" placeholder="username" maxlength="32">' +
        '</div>' +

        '<div class="mb-3">' +
        '<label class="form-label fw-semibold">Password</label>' +
        '<input type="password" class="form-control" id="new-password" placeholder="min 6 chars">' +
        '</div>' +

        '<div class="mb-4">' +
        '<label class="form-label fw-semibold">Role</label>' +
        '<select class="form-control" id="new-role">' +
        '<option value="viewer">viewer</option>' +
        '<option value="admin">admin</option>' +
        '</select>' +
        '</div>' +

        '<div id="create-result" class="mb-3"></div>' +

        '<button class="btn btn-cisco" onclick="createUser()">' +
        '<i class="bi bi-person-plus me-1"></i>Create User</button>' +

        '</div></div></div>' +

        // 오른쪽: 사용자 목록
        '<div class="col-12 col-lg-7">' +
        '<div class="panel">' +
        '<div class="panel-header d-flex justify-content-between align-items-center">' +
        '<span>User List</span>' +
        '<span class="badge bg-secondary" id="users-total">-</span>' +
        '</div>' +
        '<div class="panel-body p-0">' +
        '<table class="table table-sm mb-0" id="users-table">' +
        '<thead><tr>' +
        '<th class="px-3">Username</th>' +
        '<th>Role</th>' +
        '<th>Actions</th>' +
        '</tr></thead>' +
        '<tbody id="users-tbody">' +
        '<tr><td colspan="3" class="text-center py-3" style="color:var(--text-muted);">Loading...</td></tr>' +
        '</tbody>' +
        '</table>' +
        '</div></div></div>' +

        '</div>' +

        // 비밀번호 변경 모달 (Bootstrap modal)
        '<div class="modal fade" id="pw-modal" tabindex="-1">' +
        '<div class="modal-dialog">' +
        '<div class="modal-content">' +
        '<div class="modal-header">' +
        '<h5 class="modal-title"><i class="bi bi-key me-2"></i>Change Password</h5>' +
        '<button type="button" class="btn-close btn-close-white" onclick="closePwModal()"></button>' +
        '</div>' +
        '<div class="modal-body">' +
        '<div class="mb-3">' +
        '<label class="form-label fw-semibold">Target User</label>' +
        '<input type="text" class="form-control" id="pw-target-username" readonly>' +
        '</div>' +
        '<div class="mb-3">' +
        '<label class="form-label fw-semibold">New Password</label>' +
        '<input type="password" class="form-control" id="pw-new" placeholder="min 6 chars">' +
        '</div>' +
        '<div id="pw-result"></div>' +
        '</div>' +
        '<div class="modal-footer">' +
        '<button class="btn btn-outline-secondary btn-sm" onclick="closePwModal()">Cancel</button>' +
        '<button class="btn btn-cisco btn-sm" onclick="submitChangePassword()">' +
        '<i class="bi bi-check-circle me-1"></i>Change</button>' +
        '</div>' +
        '</div></div></div>';
}

// Bootstrap Modal 인스턴스
var _pwModal = null;

// ============================================================
// LOAD
// ============================================================
async function loadUsers() {
    var body = document.getElementById('section-body');
    if (body) body.innerHTML = _buildUsersScaffold();
    showLoading(true);

    try {
        var users = await apiFetch('/api/users');
        renderUsers(users);
    } catch (e) {
        console.error('loadUsers error:', e);
        var tbody = document.getElementById('users-tbody');
        if (tbody) {
            tbody.innerHTML =
                '<tr><td colspan="3" class="text-center py-3 text-danger">' +
                '<i class="bi bi-exclamation-circle me-1"></i>Failed to load users.</td></tr>';
        }
    }

    showLoading(false);
}

// ============================================================
// RENDER USER LIST
// ============================================================
function renderUsers(users) {
    var totalEl = document.getElementById('users-total');
    if (totalEl) totalEl.textContent = users.length;

    var tbody = document.getElementById('users-tbody');
    if (!tbody) return;

    if (users.length === 0) {
        tbody.innerHTML =
            '<tr><td colspan="3" class="text-center py-3" style="color:var(--text-muted);">' +
            'No users found.</td></tr>';
        return;
    }

    tbody.innerHTML = users.map(function (u) {
        var roleBadge = u.role === 'admin'
            ? '<span class="badge" style="background:rgba(4,159,212,0.2);color:#049fd4;border:1px solid rgba(4,159,212,0.3);">admin</span>'
            : '<span class="badge" style="background:rgba(34,197,94,0.15);color:#22c55e;border:1px solid rgba(34,197,94,0.25);">viewer</span>';

        var isSelf = (currentUser && u.username === currentUser.username);
        var deleteBtn = isSelf
            ? '<span style="color:var(--text-muted);font-size:0.78rem;margin-left:4px;">current</span>'
            : '<button class="btn btn-outline-danger btn-sm ms-1" onclick="deleteUser(\'' + escHtml(u.username) + '\')">' +
              '<i class="bi bi-trash"></i></button>';

        return '<tr>' +
            '<td class="px-3" style="font-weight:600;">' + escHtml(u.username) + '</td>' +
            '<td>' + roleBadge + '</td>' +
            '<td>' +
            '<button class="btn btn-outline-secondary btn-sm" onclick="openPwModal(\'' + escHtml(u.username) + '\')">' +
            '<i class="bi bi-key"></i> PW</button>' +
            deleteBtn +
            '</td>' +
            '</tr>';
    }).join('');
}

// ============================================================
// CREATE USER
// ============================================================
async function createUser() {
    var username  = document.getElementById('new-username').value.trim();
    var password  = document.getElementById('new-password').value;
    var role      = document.getElementById('new-role').value;
    var resultEl  = document.getElementById('create-result');

    if (!username || !password) {
        resultEl.innerHTML =
            '<div class="alert alert-warning py-2">' +
            '<i class="bi bi-exclamation-triangle me-1"></i>Username and password are required.</div>';
        return;
    }

    try {
        await apiFetch('/api/users', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: username, password: password, role: role }),
        });
        resultEl.innerHTML =
            '<div class="alert alert-success py-2">' +
            '<i class="bi bi-check-circle me-1"></i>User \'' + escHtml(username) + '\' created.</div>';
        document.getElementById('new-username').value = '';
        document.getElementById('new-password').value = '';
        var users = await apiFetch('/api/users');
        renderUsers(users);
    } catch (e) {
        resultEl.innerHTML =
            '<div class="alert alert-danger py-2">' +
            '<i class="bi bi-x-circle me-1"></i>' + escHtml(e.message || 'Failed to create user.') + '</div>';
    }
}

// ============================================================
// DELETE USER
// ============================================================
async function deleteUser(username) {
    if (!confirm('Delete user \'' + username + '\'?')) return;

    try {
        await apiFetch('/api/users/' + encodeURIComponent(username), { method: 'DELETE' });
        var users = await apiFetch('/api/users');
        renderUsers(users);
    } catch (e) {
        alert(e.message || 'Failed to delete user.');
    }
}

// ============================================================
// CHANGE PASSWORD MODAL — Bootstrap Modal 사용
// ============================================================
function openPwModal(username) {
    document.getElementById('pw-target-username').value = username;
    document.getElementById('pw-new').value = '';
    document.getElementById('pw-result').innerHTML = '';

    var modalEl = document.getElementById('pw-modal');
    _pwModal = new bootstrap.Modal(modalEl);
    _pwModal.show();
}

function closePwModal() {
    if (_pwModal) {
        _pwModal.hide();
        _pwModal = null;
    }
}

async function submitChangePassword() {
    var username = document.getElementById('pw-target-username').value;
    var newPw    = document.getElementById('pw-new').value;
    var resultEl = document.getElementById('pw-result');

    if (!newPw || newPw.length < 6) {
        resultEl.innerHTML =
            '<div class="alert alert-warning py-2">' +
            '<i class="bi bi-exclamation-triangle me-1"></i>Password must be at least 6 characters.</div>';
        return;
    }

    try {
        await apiFetch('/api/users/' + encodeURIComponent(username) + '/password', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ new_password: newPw }),
        });
        resultEl.innerHTML =
            '<div class="alert alert-success py-2">' +
            '<i class="bi bi-check-circle me-1"></i>Password changed successfully.</div>';
        setTimeout(closePwModal, 1000);
    } catch (e) {
        resultEl.innerHTML =
            '<div class="alert alert-danger py-2">' +
            '<i class="bi bi-x-circle me-1"></i>' + escHtml(e.message || 'Failed.') + '</div>';
    }
}