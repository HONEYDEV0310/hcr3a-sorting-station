# 선별장 Zenoh 실행·재점검

기준일: 2026-10-28. [Confluence 선별장 Zenoh 세팅](https://robot3final.atlassian.net/wiki/spaces/3/pages/51445763/Zenoh) v2와 현재 코드를 기준으로 한다. 이전 Domain 24 / Wi-Fi 직접 DDS 안내보다 이 문서를 우선한다.

## 통신 구성

```text
관제 Zenoh 라우터 tcp/192.168.0.20:7447
                 ↕ Zenoh TCP
선별장 zenoh-bridge-ros2dds
                 ↕ localhost CycloneDDS / ROS_DOMAIN_ID=77
선별장 ROS 서버 + 같은 PC의 더미 관제
                 ↕ Modbus TCP
HCR 192.168.3.100 ← PC 192.168.3.2:502
```

`rmw_zenoh_cpp`로 전환하는 방식이 아니다. PC 내부 ROS는 `rmw_cyclonedds_cpp`를 쓰고, 외부 관제 통신을 `zenoh-bridge-ros2dds`가 중계한다. `farm_interfaces` Action/Status/복구 Service와 HCR 프로토콜은 동일하다.

현재 설정은 `config/sorting_station.json`에 있다.

| 설정 | 값 |
|---|---|
| ros_domain_id | 77 |
| dds_config | config/cyclonedds_zenoh.xml (127.0.0.1) |
| zenoh_endpoint | tcp/192.168.0.20:7447 |
| receive_enabled | false |
| modbus_host / modbus_peer | 192.168.3.2 / 192.168.3.100 |

관제 라우터 IP가 바뀌면 `zenoh_endpoint`를 수정한다. 이전 `cyclonedds_lan.xml`의 Wi-Fi 이름이나 peer를 수정할 필요는 없다.

## 실행

이전 서버·웹캠·수동으로 실행한 선별장 Zenoh 브리지는 작업 종료 후 종료한다. 통합 실행기가 브리지도 관리하므로 같은 PC에서 중복으로 켜지 않는다. 관제 측 라우터는 관제 PC에서 실행되어 있어야 한다.

데스크탑 일반 사용자 터미널:

```bash
cd ~/manyfarm_ws/hcr3a-sorting-station
bash start_sorting.sh
```

sudo 비밀번호가 필요하면 입력한다. 실행기는 다음을 수행한다.

1. Domain 77 / localhost CycloneDDS 환경을 설정하고 이전 discovery/peer/FastDDS 설정을 제거한다.
2. `sudo ip link set lo multicast on`으로 PC 내부 DDS discovery에 필요한 loopback multicast를 활성화한다.
3. 일반 사용자로 웹캠과 Zenoh 브리지, sudo로 Modbus 서버를 실행한다.

브리지 실행 명령은 Confluence와 동일하다.

```bash
zenoh-bridge-ros2dds --domain 77 --ros-localhost-only \
  --no-multicast-scouting -e tcp/192.168.0.20:7447
```

통합 실행 중에는 이 명령을 별도로 실행하지 않는다. 실행만으로 Goal을 보내지 않는다. 반입 가능을 확인하고 관제 운영을 할 때는 기본 명령 대신 `bash start_sorting.sh --allow-receive`를 사용한다.

외장 카메라를 명시하려면 `bash start_sorting.sh --camera /dev/v4l/by-id/실제_카메라_경로`로 실행한다. 설정·명령만 확인할 때는 `bash start_sorting.sh --dry-run`을 사용한다. dry-run은 하드웨어·네트워크 연결 검증이 아니다.

## 웹캠 ROI 재설정

이전 설정이 `/dev/video4`, 현재 입력이 `/dev/video0`처럼 달라지거나 해상도가 바뀌면 기존 ROI를 자동 적용하지 않는다. `zones.backup-<고유번호>.json`으로 원본을 백업하고 구역이 비어 있는 미리보기를 연다. 원래 `zones.json`은 새로 저장하기 전까지 유지된다.

카메라 창에서 a → A 드래그, b → B 드래그, c → C 드래그, d → D 드래그, s → 저장한다. 네 구역 지정 전에는 카메라 ready=false다. 실제 구역과 색상 판정을 확인한 뒤 시험한다. 작업 중에는 ROI 편집·일시정지·종료를 하지 않는다.

## 상태 확인과 한 개 운반 시험

펜던트의 HOME·이동 경로를 확인하고 메인 및 STATE_TX를 실행한다. 별도 터미널:

```bash
cd ~/manyfarm_ws/hcr3a-sorting-station
bash start_sorting.sh --dummy
```

더미는 같은 Domain 77 / localhost 설정을 사용하며 웹캠·서버·브리지를 추가 실행하지 않는다.

- p + Enter: `state=IDLE`, `ready=True`, `error=NONE` 확인.
- 실제 관제 신규 배정을 보류하고 A에만 빨강 한 개를 준비한 뒤 s + Enter: 실제 선별 요청.
- 집기 → 배출 → HOME → READY 및 빨강 1회 집계를 확인. 네 구역 NO_COLOR 연속 3초면 SUCCESS.
- c + Enter: 더미가 시작한 작업 취소. 진행 중 한 회 운반과 복귀를 마친 뒤 최종 Result 확인.
- 원인 해결·HCR_STATE=1·HCR_ERROR=0·카메라 정상·작업 종료 후 r + Enter: 오류 복구. p로 다시 준비 상태 확인.

카메라 창의 c는 C구역 편집이다. 취소는 관제 터미널에서 입력한다. 취소와 프로세스 종료는 물리 비상정지 명령이 아니다.

로컬 ready는 웹캠·HCR의 준비 상태이며 외부 Zenoh 연결 성공을 보장하지 않는다. 실제 관제에서 `/sorter_01/status` 수신 → Goal 수락 → Feedback → Result를 별도로 확인한다. 두 PC의 인터페이스 정의가 같아야 한다.

## 진단과 종료

현재 실행 환경을 진단용 터미널에 불러온다.

```bash
cd ~/manyfarm_ws/hcr3a-sorting-station
source /opt/ros/jazzy/setup.bash
source outputs/sorting_station/ros2/install/setup.bash
source outputs/sorting_station/launcher/ros_env.sh
ros2 topic echo /sorter_01/status --once
```

최신 실행 폴더 `outputs/sorting_station/launcher/날짜_시각/`에 `bridge.log`, `webcam.log`, `server.log`, `settings.json`이 있다. 관제 미연결은 `bridge.log`와 관제 라우터 주소·7447 포트 접근을 먼저 확인한다. 현재 실행 로그 폴더는 시작 터미널에 표시된다. 웹캠/HCR 준비 오류는 아래에서 확인한다.

```bash
python3 -m json.tool outputs/sorting_station/hcr_runtime/runtime.json
```

작업 완료 또는 취소의 최종 Result와 HOME 복귀 후 실행 터미널에서 Ctrl+C. 실행기가 자신이 시작한 서버·웹캠·브리지를 정리한다. 저널을 지워 오류를 우회하지 않는다.

## 설치와 검증 범위

기존 PC에 CycloneDDS와 `zenoh-bridge-ros2dds`가 설치되어 있으면 이번 설정 변경에 재빌드는 필요 없다. 신규 PC에는 ROS Jazzy와 시스템 OpenCV/NumPy를 설치하고 기존 `build_sorter.sh`로 빌드한다. Zenoh 브리지 패키지 저장소 등록·설치는 위 Confluence의 패키지 설치 절차를 따른다. 실행기는 누락된 브리지 설치를 안내하며 자동 설치하지 않는다.

카메라/ROI/localhost Modbus 8개, 실행기 환경·브리지 명령·복구 환경·더미 중복 방지·프로세스 정리 12개 테스트가 통과했다. 통합/더미 dry-run과 셸 문법·Python 구문 검사도 통과했다. 실제 USB 웹캠 GUI, HCR 운반, 두 PC 간 Zenoh 연결은 새로 실행하지 않았으며 현장 확인 대상이다.
