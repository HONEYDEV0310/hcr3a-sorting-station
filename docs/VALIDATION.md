# 배포 준비 검증 — 2026-09-28

- 원본: manyfarm_robotarm/src/sorting_station 실물 전용 수집기.
- 변경: 개인 Python 절대 경로 제거, 저장소 내부 보정 디렉터리 지정, 고정 LeRobot 버전, GUI OpenCV 설치, USB 고유 경로, 모터 비접속 doctor, 종료 카메라 예외 정리, arming 직전 관측 신선도/유한값 확인.
- 별도 소스 수정 없이 follower 위치 읽기에 num_retry=2 사용(기존 PC의 LeRobot 로컬 수정과 동일 취지).
- 단위4개 PASS: 급격한 초기 명령 제한, 추종 오차 제한, NaN 거부, 저장 수 기준 색상 교대.
- native LeRobot 통합 PASS: 폐기한 시연 제외, top/wrist 합성 RGB3프레임 저장, finalize, 재로드, 이미지 디코딩 및 action 일치.
- Python/Bash/JSON 구문 PASS.
- 설치된 LeRobot0.4.4 / torch2.10.0 환경으로 데이터셋 통합 시험. 완전히 빈 PC의 전체 setup 설치는 미실행. 의존성 전체의 hash lock은 아니며 LeRobot 소스 커밋/주요 패키지 버전을 고정한 구성이다.
- 실제 모터 구동, 실제 두 카메라 동시 스트리밍, 장기간30Hz 유지, 네트워크에 배포한 후 clone 검증은 미실행. 장치 준비 후2개 에피소드로 먼저 점검한다.
- RGB만 지원; depth/카메라 하드웨어 타임스탬프/자동 성공 판정/기존 세션 이어쓰기는 미지원.

## 2026-10-01 HCR ROS 실행기 동기화

- 독립 sorting 저장소에서 smartfarm_interfaces/hcr_sorting colcon 빌드 성공.
- 런타임 단위 테스트 17개, 기존 카메라 테스트 6개 통과.
- 실제 ROS Action + localhost Modbus 통합 시험 통과: A빨강 2회/B노랑 1회 SUCCESS, 중복 task 거절, 더미 관제 시작/피드백/중복 시작 차단/취소 후 1회 완료 Result 수신.
- PDF 전체 페이지 렌더링 검토. 실물 로봇에 명령을 보내지 않았으며 Rodi 반복 쓰기/모션/그리퍼 현장 검증은 남아 있음.

## 2026-10-07 farm_interfaces 패키지 통일

- `farm_interfaces`와 `hcr_sorting` colcon 빌드 성공.
- 기존 SortBatch.action/SorterStatus.msg의 바이트·필드·자료형·선언 순서 보존 확인.
- 설치된 서버·더미 관제가 새 farm_interfaces 타입을 import하고 생성된 type support를 로드하는지 확인.
- `ros2 interface show farm_interfaces/action/SortBatch` 및 `farm_interfaces/msg/SorterStatus` 확인.
- 상태 머신 14개, Modbus 레지스터 처리 2개, 더미 관제 복구 7개 테스트 통과.
- 관제 공유본: `outputs/sorting_station/interface_share/farm_interfaces_sorter.tar.gz`, 원본 체크섬은 같은 폴더의 SHA256SUMS.
- 실행 중인 서버는 재시작하지 않았다. 도구 환경의 네트워크 접근 제한으로 두 PC의 Status→Goal→Feedback→Result 실통신 시험은 미실행이며, 관제와 전환 시점을 맞춰 확인해야 한다.

## 2026-10-07 통합 실행 도구와 Confluence 재정리

- start_sorting.sh / scripts/start_sorting_station.py / config/sorting_station.json 추가.
- 통합 실행 도구7개 테스트 통과: DDS·peer 명시, IPv4 누락, 카메라 일반 사용자/반입 기본false, 설정 검증, 프로그램 실패·부분 실행 실패·사용자 중단 시 자식 정리.
- 정상/더미 dry-run과 Bash 구문 확인. 실제 장비·sudo 서버는 새로 시작하지 않았다.
- Confluence 메인 인수인계와 상세6개·통신 프로토콜 총8개 페이지 갱신 후 읽기 검증. 원본 사진 media 속성 보존 확인.
- 현재 운영 원본: docs/hcr3a/08_CURRENT_OPERATIONS.md. 다른 Codex 채팅 원문을 조회했다는 의미가 아니며 기존 문서와 현장 기록을 참고했다.
