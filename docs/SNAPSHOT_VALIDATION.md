# 개인 스냅샷 검증

정리·검사일: 2026-11-05. 현재 작업 폴더에서 HCR 선별장 관련 파일을 추출한 후 검사했다. 기존 운영 코드는 수정하지 않았다.

## 실행한 검사

| 검사 | 결과 |
|---|---|
| 통합 실행기·환경·프로세스 정리 | unittest 12개 통과 |
| 배치 상태기계·고장 보존·취소·중복 방지 | unittest 14개 통과 |
| Modbus 레지스터·localhost TCP | unittest 3개 통과 |
| 카메라 판정·ROI 불일치·백업·localhost preview bridge | unittest 8개 통과 |
| 합계 | 37개 통과 |
| 통합/더미 실행기 | --dry-run 확인 |
| Bash 실행 스크립트 | 파일별 bash -n 검사 |
| Python / JSON / package.xml / DDS XML | 구문 파싱 검사 |
| Markdown 상대 파일 링크 | 파일 존재 검사 |
| 게시 파일 구성 | 인증정보 패턴·로그·DB·빌드·venv·장치별 ROI 제외 확인 |

회귀 시험 진입점은 `bash scripts/check_sorting.sh`이다. localhost 테스트 소켓을 사용하므로 소켓이 금지된 샌드박스에서는 네트워크 시험이 실패할 수 있다. 이 시험은 192.168.3.100 등 실물 장비에 접속하지 않는다.

## 이번에 실행하지 않은 검증

- 신규 PC 전체 설치 및 ROS 패키지 재빌드
- ROS 의존 더미 관제·통합 시험의 재실행
- 실제 USB 웹캠 GUI·마우스 ROI 설정
- 실제 HCR 모션·그리퍼·파지 성공률
- 두 PC 사이 Zenoh TCP 연결, 관제 Status/Goal/Feedback/Result 종합 시험
- 펜던트 8구역/색상 조합의 새 현장 시험

위 항목의 과거 기록은 [검증 이력](hcr3a/06_VALIDATION_HISTORY.md)과 [운영 기록](hcr3a/08_CURRENT_OPERATIONS.md)에 작성 당시 기준으로 보존한다. 현재 설정 파일이 올바르다는 사실을 실제 네트워크 접속 성공으로 해석하지 않는다.

추출 파일 목록과 SHA-256은 루트 `SNAPSHOT_MANIFEST.json`에 기록한다. 매니페스트 자신과 Git 메타데이터·생성물은 해시 대상에서 제외한다.
