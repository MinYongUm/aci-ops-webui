// ============================================
// auth.js
// 목적: 현재 사용자 정보 로드, 로그아웃 처리
// ============================================

/* global apiFetch, navigateTo */

var currentUser = null;  // {username, role}

// ============================================
// 현재 사용자 정보 로드 (페이지 초기화 시 호출)
// ============================================
async function loadCurrentUser() {
    try {
        var data = await apiFetch('/api/auth/me');
        currentUser = data;
        _renderUserBar(data);
        _applyRoleVisibility(data.role);
    } catch (e) {
        // 401: 쿠키 만료 → 로그인 페이지로
        window.location.href = '/login';
    }
}

// ============================================
// 사이드바 하단 사용자 정보 렌더링
// ============================================
function _renderUserBar(user) {
    var usernameEl = document.getElementById('sidebar-username');
    var roleEl = document.getElementById('sidebar-role');

    if (usernameEl) usernameEl.textContent = user.username;
    if (roleEl) {
        roleEl.textContent = user.role.toUpperCase();
        roleEl.className = 'sidebar-role-badge ' + (user.role === 'admin' ? 'role-admin' : 'role-viewer');
    }
}

// ============================================
// 역할에 따른 UI 요소 표시/숨김
// ============================================
function _applyRoleVisibility(role) {
    // admin 전용 요소: Settings, Users 메뉴
    var adminOnly = document.querySelectorAll('.admin-only');
    adminOnly.forEach(function(el) {
        el.style.display = (role === 'admin') ? '' : 'none';
    });
}

// ============================================
// 로그아웃
// ============================================
async function doLogout() {
    try {
        await fetch('/api/auth/logout', { method: 'POST' });
    } catch (e) {
        // 무시 — 쿠키 삭제가 목적
    }
    window.location.href = '/login';
}