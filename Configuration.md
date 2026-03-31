# 설정 가이드

## APIC 연결 설정

`/setup` 페이지에서 GUI로 입력하거나, `config.yaml`을 직접 작성할 수 있습니다.

```yaml
apic:
  hosts:
    - "https://APIC1_IP"   # Primary
    - "https://APIC2_IP"   # Failover (클러스터 구성 시)
    - "https://APIC3_IP"   # Failover (클러스터 구성 시)
  username: "계정명"
  password: "비밀번호"
  timeout: 30
  retry: 3
linter:
  naming:
    enabled: true
    tenant_prefix: "TN-"
    bd_prefix: "BD-"
    epg_prefix: "EPG-"
    contract_prefix: "CON-"
    ap_prefix: "AP-"
```

APIC 단독(1대) 구성은 `hosts`에 1개만 입력합니다.
Primary 연결 실패 시 다음 host로 자동 전환(Failover)됩니다.


## 인증 및 접속 흐름

```
브라우저 접속 → /login (앱 계정 로그인)
               → APIC 미설정 시 /setup (APIC 접속 정보 입력)
               → Dashboard
```

> 로그인 화면의 앱 계정과 `/setup`에서 입력하는 APIC 계정은 별도입니다.

최초 설치 시 기본 계정이 자동 생성됩니다.

| 항목 | 값 |
|------|-----|
| 기본 계정 | admin |
| 기본 비밀번호 | aci-ops-admin |

로그인 후 Settings > Users 메뉴에서 비밀번호 변경 및 추가 계정을 생성할 수 있습니다.

### 역할

| 역할 | 권한 |
|------|------|
| admin | 전체 기능 + 설정 변경 + 사용자 관리 |
| viewer | 대시보드 조회만 가능 |


## Config Linter 규칙

ACI 설정의 보안 취약점과 Best Practice 위반을 자동으로 탐지합니다.

| Rule ID | 분류 | 심각도 | 탐지 내용 |
|---------|------|--------|-----------|
| SEC-001 | Security | critical | permitAll 계열 위험 Contract |
| SEC-002 | Security | warning | Subject 없는 빈 Contract |
| SEC-003 | Security | warning | Filter 없는 빈 Subject |
| BP-001 | Best Practice | critical | BD 미연결 EPG |
| BP-002 | Best Practice | warning | Contract 미연결 고립 EPG |
| BP-003 | Best Practice | warning | Subnet 없는 BD |
| NM-001 | Naming | warning | 이름 내 공백/특수문자 |
| NM-002 | Naming | warning | Prefix 규칙 위반 (config.yaml 정의 시) |

Live Scan과 APIC export JSON 파일 업로드 두 가지 방식을 지원합니다.