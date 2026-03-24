# Changelog

## [1.2.0] - 2026-03-24
### Added
- tests/test_api.py: pytest 기반 API 엔드포인트 단위 테스트 (ACIClient Mock 처리)
- tests/conftest.py: pytest 사전 패치 설정 (config.yaml, StaticFiles 없이 실행)

### Changed
- README.md: 대시보드 스크린샷 추가

## [1.1.0] - 2026-02-04
### Added
- 자동 새로고침 기능 (30초)
- Endpoint 검색 API (/api/endpoint/search)
- MAC/IP 검색 UI
- 다크/라이트 테마 전환
- CSV 내보내기
- Fault 상세 모달
- 하단 상태 바 (마지막 업데이트 시간)
- Capacity 섹션 추가

### Changed
- UI 레이아웃 개선
- 토폴로지 시각화 개선

## [1.0.0] - 2026-02-04
### Added
- FastAPI 백엔드 (7개 API)
- Bootstrap 대시보드 UI
- 3가지 테마 (기본, 다크, 기업용)
- Health Check, Policy, Interface, Endpoint, Audit, Capacity, Topology 모듈