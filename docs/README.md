# 선별장 자료 목차

## 현재 실행과 통신

- [Zenoh 실행·ROI·복구·종료](hcr3a/09_ZENOH_START.md): 현재 실행 기준. localhost CycloneDDS / Domain 77.
- [manyfarm5G·관제팀 통신 테스트](hcr3a/10_ZENOH_TEAM_TEST.md): 인터넷 없는 현장용 절차.
- [전체 운영과 구현 정리](hcr3a/08_CURRENT_OPERATIONS.md): 제어 구조·저널·오류·완료 조건.
- [ROS/Modbus 프로토콜](hcr3a/07_PROTOCOL_REFERENCE.md): Action·Status·Service와 레지스터.
- [인터페이스 변경 이력](INTERFACES.md), [설계 결정](DECISIONS.md).

## 장치별 자료

- [설치와 네트워크](hcr3a/01_SETUP.md)
- [카메라·ROI·색상 판정](hcr3a/02_VISION.md)
- [Rodi·티칭·그리퍼](hcr3a/03_RODI_GRIPPER.md)
- [오류별 점검](hcr3a/05_TROUBLESHOOTING.md)
- [관제와 공유할 Action/Message 코드](../src/farm_interfaces/)

## 검증·출처

- [검증 결과와 산출물 이력](hcr3a/06_VALIDATION_HISTORY.md)
- [개인 스냅샷 검증](SNAPSHOT_VALIDATION.md)
- [출처·포함/제외 범위](../NOTICE.md)
- [문서 링크가 있는 Confluence 원본](hcr3a/CONFLUENCE_PAGES.json): 접근 권한과 인터넷 연결이 필요하며 로컬 문서도 함께 보존한다.

## 과거 인수인계와 작성 참고자료

아래 자료는 당시 상태와 시행착오를 보존합니다. 실행 설정은 현재 문서를 우선합니다. 특히 Domain 24·직접 LAN DDS·이전 preview 레지스터 맵은 현재 자동 선별 실행과 혼용하지 않습니다.

- [2026-10-06 데스크탑 인수인계](HCR3A_DESKTOP_HANDOFF.md)
- [초기 노트북 시작](HCR_LAPTOP_START.md), [작업공간](HCR_WORKSPACE.md)
- [과거 실행·테스트·종료](hcr3a/04_OPERATIONS.md)
- [Rodi 프로그래밍 가이드](../src/sorting_station/hcr_sorting/RODI_PROGRAMMING_GUIDE_KR.md)
- [단계별 메인 프로그램 PDF](HCR3A_MAIN_PROGRAM_STEP_BY_STEP_KR.pdf)
- [Rodi 워크북 PDF](HCR3A_RODI_WORKBOOK_KR.pdf)
- [초기 기획](../src/sorting_station/HCR3A_SORTING_HANDOFF.md), [2026-10-01 인계](../src/sorting_station/HCR3A_CURRENT_HANDOFF.md)
- [반입 당시 파일 매니페스트](IMPORT_MANIFEST.json): 이번 개인 저장소의 파일 해시 목록이 아니다.

PDF와 텍스트 가이드는 펜던트의 네이티브 프로그램·좌표 백업을 대체하지 않습니다.
