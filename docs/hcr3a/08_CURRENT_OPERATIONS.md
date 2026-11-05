# HCR-3A 선별장 현재 운영 기준과 전체 작업 정리

> 2026-10-28 통신 변경: [Zenoh 실행·재점검](09_ZENOH_START.md)을 우선한다. 통합 실행기는 웹캠·서버·Zenoh 브리지를 함께 실행한다. PC 내부 localhost CycloneDDS / Domain 77, 외부 관제는 tcp/192.168.0.20:7447이다.

정리일: 2026-10-07. 현재 코드는 `farm_interfaces`를 사용한다. 이 문서는 기존 인수인계와 Confluence 상세 문서, 저장소 코드·검증 기록, 이번 대화의 현장 로그를 합친 운영 기준이다. 다른 Codex 채팅의 원문은 직접 조회하지 못했으며 그 작업이 남긴 문서와 기록을 참고했다. 확인된 사실·사용자 보고·미확정 원인을 구분한다.

## 1. 매일 실행하는 방법

기존 웹캠·서버를 종료한 상태에서 데스크탑 터미널 하나만 연다.

```bash
cd ~/manyfarm_ws/hcr3a-sorting-station
bash start_sorting.sh
```

sudo 비밀번호가 필요하면 입력한다. 외장 웹캠 창과 HCR 서버, Zenoh 브리지가 함께 실행된다. 웹캠과 브리지는 일반 사용자로, Modbus 서버만 sudo 권한으로 실행한다. 실행기는 loopback multicast 활성화에도 sudo를 사용한다. 터미널에는 준비 상태와 오류, 로그 위치가 표시된다. 실행만으로 로봇 작업을 시작하지 않는다. 실제 선별 시작은 관제가 배정한다.

물량을 내려놓아도 되는 상태를 운영자가 확인했을 때만:

```bash
bash start_sorting.sh --allow-receive
```

이 옵션은 `receive_enabled=true`를 설정한다. 반입 센서를 확인하거나 하역 성공을 인증하는 기능은 아니다. 기본값 false에서는 장치가 준비되어도 receive_ready는 false다.

다른 외장 카메라를 지정하려면:

```bash
bash start_sorting.sh --camera /dev/v4l/by-id/실제_카메라_경로
```

실행할 명령만 확인하려면 `bash start_sorting.sh --dry-run`을 사용한다. 하드웨어와 sudo에 접근하지 않으며 실제 장치 준비를 검증하는 명령은 아니다.

종료는 관제에서 작업 완료 또는 Cancel 후 최종 Result와 로봇 복귀를 확인한 뒤 Ctrl+C로 한다. 카메라 창을 닫거나 한 프로그램이 종료되면 이 도구가 함께 시작한 다른 프로그램도 종료한다. 프로세스 종료는 물리 비상정지가 아니다. 통합 실행기는 자동 Goal·자동 복구·자동 재시작을 수행하지 않는다.

## 2. 실행 설정과 기록

`config/sorting_station.json`에서 카메라, 반입 허용, DDS XML 경로와 Modbus 주소를 설정한다. 프로그램 코드를 고치거나 매번 환경변수를 입력할 필요가 없다.

| 설정 | 기본값 | 의미 |
|---|---|---|
| ros_domain_id | 77 | 선별장 PC 내부 ROS 도메인 |
| dds_config | config/cyclonedds_zenoh.xml | localhost DDS 설정 |
| zenoh_endpoint | tcp/192.168.0.20:7447 | 외부 관제 Zenoh 연결 주소 |
| camera | null | 확인된 Wed Camera 외장 웹캠 자동 선택 |
| receive_enabled | false | 운영자가 확인한 반입 허용 |
| modbus_host | 192.168.3.2 | PC 유선 서버 주소 |
| modbus_port | 502 | Modbus TCP 포트 |
| modbus_peer | 192.168.3.100 | 접속을 허용할 HCR 주소 |

현재 XML은 127.0.0.1만 사용한다. 관제 IP가 바뀌면 sorting_station.json의 zenoh_endpoint를 변경한다. 통합 실행기는 이전 Tailscale DDS·ROS_STATIC_PEERS·ROS_DISCOVERY_SERVER·FastDDS 환경변수를 제거하고 localhost CycloneDDS / Domain 77을 적용한다. 관제 연결은 Zenoh 브리지가 담당한다. 이전 cyclonedds_lan.xml은 과거 직접 DDS 연결용이며 현재 기본값이 아니다.

| 파일 | 내용 |
|---|---|
| outputs/sorting_station/launcher/날짜_시각/webcam.log | 카메라 로그 |
| 같은 폴더의 server.log | 실행기 시작·Goal 거절·오류 로그 |
| 같은 폴더의 bridge.log | Zenoh 브리지·관제 연결 로그 |
| 같은 폴더의 settings.json | 해당 실행의 설정 |
| outputs/sorting_station/launcher/ros_env.sh | 실행기에 적용한 ROS 환경 |
| outputs/sorting_station/hcr_runtime/runtime.json | phase/ready/HCR/카메라/오류·개수 |
| outputs/sorting_station/hcr_runtime/journal.sqlite3 | 영속 작업·개수·JOB 번호·오류 |
| outputs/sorting_station/hcr_preview/zones.json | 카메라 구역 설정 |
| outputs/sorting_station/hcr_preview/state.json | 최신 카메라 관측 |

중복 통합 실행은 파일 잠금으로 거부한다. 수동 서버 등으로 Modbus 포트가 사용 중이면 실행을 거부하며 기존 프로세스를 강제로 종료하지 않는다. 웹캠·서버 실행 실패 시 자신이 시작한 프로세스만 정리한다.

## 3. 더미 관제와 오류 복구

통합 실행기와 같은 설정으로 더미 관제를 여는 방법:

```bash
cd ~/manyfarm_ws/hcr3a-sorting-station
bash start_sorting.sh --dummy
```

이 명령은 웹캠이나 서버를 추가로 켜지 않는다. 다른 설정 파일을 사용했다면 --dummy에도 같은 --config 경로를 지정한다.

| 키+Enter | 기능 |
|---|---|
| p | 상태·준비·오류 확인 |
| r | 수동 오류 복구 요청 |
| c | 현재 더미 관제가 시작한 작업 취소 |
| s | 실제 선별 작업 시작 |
| q | 더미 관제 종료 |

실제 관제의 작업을 더미 관제가 자동 추적·취소하는 것은 아니다. 복구용으로 열었다면 s를 누르지 않는다. 실제 관제의 신규 배정을 먼저 보류하고, 로봇·물체 상태와 작업 종료를 확인한다. 펜던트에서 원인을 해결해 HCR_STATE=1, HCR_ERROR=0으로 정상화하고 카메라가 준비된 뒤 r을 호출한다. 성공 후 새 상태에서 ready=true/error=NONE을 확인한다. 이전 작업의 실패 결과와 완료 수량은 관제에 보존한다.

현재 실행기에 적용된 설정을 그대로 다른 터미널에 불러오려면:

```bash
source outputs/sorting_station/launcher/ros_env.sh
```

복구 서비스는 `/sorter_01/reset_fault`, 타입은 `std_srvs/srv/Trigger`다. 서비스는 PC에 저장된 오류를 해제한다. 펜던트 경보를 직접 해제하거나 로봇을 이동하지 않는다. 재시작·저널 삭제로 오류를 우회하지 않는다.

## 4. 장비와 역할

```text
USB 웹캠 → A/B/C/D ROI와 HSV 판정 → state.json
                                          ↓
관제 → ROS SortBatch Goal → PC hcr_sorter ↔ Modbus TCP ↔ HCR/Rodi
관제 ← Status/Feedback/Result                     PICK → 배출 → HOME
```

PC는 ROS 작업과 개수·JOB을 관리하고, HCR Rodi가 티칭 경로와 그리퍼를 제어한다. PC가 관절 좌표를 보내는 구조가 아니다. HCR은 Modbus 클라이언트이며 PC가 서버다.

노트북의 확인된 유선 구성은 enp3s0=192.168.3.2/24, HCR=192.168.3.100/24다. 다른 PC에서는 인터페이스 이름과 주소를 다시 확인한다. 과거 HCR 주소 .1 기록은 오기이며 .1은 현장 게이트웨이다.

manyfarm Wi-Fi는 관제 통신, 휴대폰 USB 테더링은 인터넷에 사용할 수 있다. 당시 확인한 USB 인터페이스는 enx862620f017a7이며 장치에 따라 달라진다. USB 테더링 기본 경로가 인터넷을 맡고 manyfarm 내부 주소는 Wi-Fi로 가는지 ip route get으로 확인한다. 기존 HCR 유선 주소는 유지한다. 관제 PC를 engineer 핫스팟으로 옮길 필요는 없다.

```bash
nmcli connection show --active
ip -br addr
ip route
ip route get 1.1.1.1
ip route get 192.168.3.100
```

manyfarm이 인터넷 기본 경로를 차지하면 실제 연결 프로필에 ipv4.never-default/ipv6.never-default를 설정한다. 적용에 따른 재연결은 작업 종료 후 수행한다. 관제망과 테더링망의 대역이 겹치거나 관제가 다른 서브넷이면 별도 라우팅 확인이 필요하다.

## 5. 카메라·선택·종료 조건

현재 경로는 OpenCV 외장 USB 웹캠이다. 자동 선택은 sysfs 이름 Wed Camera: Wed Camera와 index=0인 장치가 정확히 한 대일 때만 성공한다. 내부 노트북 카메라로 자동 대체하지 않는다. 다른 카메라는 /dev/v4l/by-id 경로를 권장한다.

카메라 창에서 a/b/c/d 각각 선택 후 드래그로 네 구역을 지정하고 s로 저장한다. Space는 일시정지, q는 종료다. 창의 c는 C구역 편집이며 취소 명령이 아니다. 작업 중 편집·일시정지·종료는 카메라 준비 실패를 일으킬 수 있다.

카메라 위치·해상도·source가 바뀌면 ROI를 다시 설정한다. 기본 HSV 판정값은 색상 면적비 .08, saturation 90, brightness 60, 안정화 .3초다. 상태는 RED/YELLOW/NO_COLOR/WAIT/MIXED이며 기본 우선순위는 ABCD다.

2026-10-28 수정: 저장된 ROI의 source/해상도가 현재 영상과 다르면 기존 JSON을 `zones.backup-<고유번호>.json` 형태로 백업하고, 구역이 비어 있는 미리보기를 연다. A/B/C/D를 다시 지정하고 s로 저장한다. 네 구역 지정 전에는 ready=false이며 기존 ROI를 다른 입력에 자동 적용하지 않는다. 원래 설정 파일은 s로 저장하기 전까지 유지된다.

한 번 선택한 명령은 BUSY 동안 고정한다. 동일 JOB의 정상 DONE에서 한 번 집계하며, READY 복귀 후 .5초 뒤 새 프레임으로 재선택한다. 같은 A에 색이 남아 있으면 새 JOB으로 반복한다. 네 구역 모두 NO_COLOR인 새 관측이 연속 3초면 SUCCESS다. WAIT/MIXED/카메라 실패는 성공 조건이 아니다. 색상 미검출은 상류 잔량이나 실제 파지 성공의 센서 인증을 뜻하지 않는다.

## 6. 현재 ROS 계약: farm_interfaces

2026-10-07 관제 요청에 따라 smartfarm_interfaces에서 farm_interfaces로 패키지명을 변경했다. 서버·더미 관제·빌드 의존성·ROS 통합 시험 코드를 함께 변경했다. 필드 이름·자료형·순서와 통신 경로는 보존했다.

| 방식 | 이름 | 타입 |
|---|---|---|
| Action | /sorter_01/sort_batch | farm_interfaces/action/SortBatch |
| Status | /sorter_01/status | farm_interfaces/msg/SorterStatus |
| 복구 Service | /sorter_01/reset_fault | std_srvs/srv/Trigger |

robot_id=sorter_01. Status는 1Hz, Feedback은 1Hz 및 단계·개수 변경 시, Result는 종료 시 발행한다. Status.state는 IDLE/SORTING/ERROR다. Feedback.phase는 SCANNING/WAIT_ACK/BUSY/WAIT_READY와 CANCEL_PENDING_ 접두사이며 종료 단계도 보고될 수 있다.

ready는 작업·저장 오류 없음, 카메라 1초 이내 최신 관측과 네 ROI 준비, HCR 주소100 쓰기 3초 이내·STATE1·ERROR0 조건을 모두 요구한다. receive_ready는 ready AND receive_enabled다.

관제는 하역·안전 이격 완료의 bucket_unload SUCCESS와 최신 ready=true를 확인한 뒤 Goal을 보낸다. 선별장 노드는 하역 Action을 직접 구독하지 않는다. get_task_state 서비스와 관제 heartbeat 구독은 현재 구현되어 있지 않다.

관제는 Feedback의 개수를 누적해서 더하지 말고 최신 누적값으로 교체하며 Result로 최종 확정한다. 실패·취소에서도 완료 수량을 보존하고, 이후 늦은 Feedback으로 최종 결과를 덮어쓰지 않는다. 부트 ID 변경과 3초 STALE/5초 OFFLINE을 관리하고 재연결 후 자동 재전송·자동 재개를 하지 않는다. 이 재연결 정책은 관제 구현 요구사항이며 구현 완료 확인은 별도다.

원본 위치는 src/farm_interfaces/action/SortBatch.action, src/farm_interfaces/msg/SorterStatus.msg다. 공유 압축파일은 outputs/sorting_station/interface_share/farm_interfaces_sorter.tar.gz다. 관제의 기존 farm_interfaces에는 두 파일과 빌드 항목을 추가하고 다른 예찰·수확 정의를 덮어쓰지 않는다. 양쪽 전환 시점을 맞춘다.

## 7. HCR Modbus와 Rodi

| 주소 | 이름 | 값 |
|---|---|---|
| 0 | PC_COMMAND | A11/12, B21/22, C31/32, D41/42; 끝자리 빨강1/노랑2 |
| 1 | PC_JOB_ID | 운반 번호 1..65535, 영속 증가·재사용 금지 |
| 2 | PC_REQUEST | 요청1, 일치 BUSY 확인 후0 |
| 3 | PC_BATCH_ACTIVE | 활성 작업1 |
| 4 | PC_HEARTBEAT | PC tick 카운터 |
| 100 | HCR_STATE | 0미준비/1READY/2BUSY/3DONE/4ERROR |
| 101 | HCR_ACK_JOB | 수락 JOB |
| 102 | HCR_DONE_JOB | 완료 JOB |
| 103 | HCR_ERROR | 0정상/비영 오류 |

PC .2:502, 허용 HCR .100, Unit1, 읽기 FC03/04, 쓰기 FC06/16. 주소40001을 더하지 않는다. 과거 읽기전용 preview의 주소1~4 의미와 호환되지 않는다.

PC COMMAND/JOB/REQUEST1 → Rodi ACK일치/STATE2 → PC REQUEST0 → 이동·놓기·HOME → DONE일치/STATE3 → PC COMMAND0/REQUEST0 → Rodi STATE1.

STATE_TX는 기준100ms(현장 사진에는50ms도 확인) 반복 송신이며 메인과 같은 state_out 변수를 공유한다. 상태100은 값이 같아도 계속 쓴다. ACK/DONE/ERROR를 먼저 갱신하고 STATE를 마지막 commit으로 쓰거나 100~103을 일관된 FC16으로 쓴다. Rodi의 DONE이 실제 놓기와 HOME 복귀를 보장해야 한다.

티칭 자산은 P_HOME/Q_HOME, P_A~D_UP/PICK, P_LEFT/P_RIGHT, Q_3/Q_34/Q_345와 PICK_A~D/PLACE_AND_RETURN이다. 안내 문서는 펜던트 네이티브 백업이 아니다. 사용자 확인 Tool I/O는 D_TOOL_OUT_0=열기, D_TOOL_OUT_1=닫기다. 최종 Reverse 설정·신호 유지시간·파지센서 조건은 전달된 자료에 없으므로 완료 사실로 추가하지 않는다.

## 8. 실제 문제와 해결 기록

| 문제 | 확인한 사실과 조치 |
|---|---|
| LAN 설정을 export해도 외부 관제 미연결 | ros_local_env.sh가 로컬 DDS로 덮어썼음. 명시적 외부 설정을 보존하도록 수정 |
| tailscale0 does not match an available interface | /home/ubuntu/cyclonedds.xml의 오래된 Tailscale 바인딩. 실제 서버 환경을 확인해야 함. 새 통합 실행기는 LAN XML을 명시 |
| 더미 관제 status 없음 | 실행기/더미 DDS 불일치와 로컬 discovery 확인 필요. 새 도구는 같은 설정과 자기 Wi-Fi IP peer 사용 |
| Goal rejected | 여러 원인을 묶던 로그를 ID·중복·장치 준비별로 상세화 |
| robot_id에 SORT, task_id에 BATCH, batch_id에 시간 수신 | 실제 로그로 필드 밀림 확인. 관제 정의 또는 생성 코드 불일치 가능성. 관제에 전체 원본 공유 |
| HCR_ERROR_2 반복 | 로봇에서 오류2를 송신, PC가 FAILED와 latch로 보존. 당시 BUSY 후 약 .6초에 오류 발생 로그 확인 |
| 오류 복구 후에도 실행 불가 | 로봇 오류0/READY1 및 카메라 정상화 후 PC reset_fault 필요. 복구 성공과 자동 재시작은 다름 |

오류2는 Rodi 작성 안내의 로컬 제안 코드로는 수락 응답 시간 초과다. 실제 펜던트에서 error_out=2를 설정하는 분기를 확인해야 의미를 확정할 수 있다. wait_count를 매 대기 진입 시0으로 초기화하고 WAIT .1초와 카운터 증가를 확인하는 방안을 제안했으며, 펜던트 변경·최종 해결 확인은 아직 전달받지 않았다. PC ack_timeout을 늘리거나 오류2를 무시하는 방식으로 해결했다고 기록하지 않는다.

기본 제한: 카메라1초/HCR3초/ACK10초/BUSY120초/READY10초/scene60초/배치1800초. SQLite는 task 중복·결과·수량·JOB번호·오류를 보존한다. 실행 중 재시작한 Task는 FAILED/PROCESS_RESTART이며 자동 재실행하지 않는다.

## 9. 설치·전환·검증

이미 구성된 노트북은 매일 재빌드할 필요가 없다. 신규 PC 또는 인터페이스 변경 때만:

```bash
source /opt/ros/jazzy/setup.bash
bash src/sorting_station/hcr/build_sorter.sh
source outputs/sorting_station/ros2/install/setup.bash
ros2 interface show farm_interfaces/action/SortBatch
ros2 interface show farm_interfaces/msg/SorterStatus
```

필요한 환경은 Ubuntu24.04/ROS Jazzy/Python3.12, colcon/rosidl/rclpy/std_srvs/rmw_cyclonedds_cpp, 시스템 OpenCV·NumPy다. 다른 PC의 빌드·venv를 복사하지 않는다. ROS 설치 명령은 기존 설치 문서를 따른다.

확인된 검증:

- 이전 기록: core14+Modbus3, 카메라6, ROS/localhost Modbus 통합, 현장 READY·BUSY/DONE·취소 후 수량 보존 확인 기록.
- 2026-10-07: farm_interfaces/hcr_sorting 빌드, 필드·자료형·순서·바이트 보존, 설치된 새 타입과 import 확인. core14+레지스터2+더미복구7=23개 통과.
- 통합 실행 도구: 실패·부분 실행 실패 시 동반 프로세스 정리, 명시적 DDS/peer, 반입 기본값과 카메라 권한, 설정 오류를 검증한7개 테스트 통과. dry-run 확인.
- 이 도구 작성 시 실제 웹캠·sudo 서버를 새로 실행하지 않았으며, 도구 환경의 네트워크 제한으로 farm_interfaces 전환 후 두 PC 통합시험은 완료하지 못했다.

현장 최종 확인은 양쪽 farm_interfaces 전환 후 Status → Goal수락 → Feedback → Result, 실패·취소 수량 보존, 복구·재연결 순서로 수행한다. 펜던트8색/구역 조합 시험표·최종 그리퍼 조건·성공률은 추가 현장 근거가 필요하다.

## 10. 전체 이력과 백업

- 초기 OMX/LeRobot 시연 수집·보정과 수확 SO-ARM101 연구는 별도 경로로 보존했으며 현재 HCR 자동 선별 경로에 넣지 않았다.
- 9/29: 상수 읽기 시험에서4ROI HSV 후보 PoC, D435 SDK·시리얼 시험, HCR IP 정정.
- 10/1: HCR 전용 ROS 배치 실행기·저널·영속 JOB·더미 관제·mock·Rodi 가이드 도입.
- 10/1~2: 유선 IP, 외장 웹캠, loopback DDS, 신호·변수·티칭·STATE_TX 작성과 현장 READY/취소 기록.
- 10/2: 카메라 읽기와 monotonic 시각 경합 수정, camera_ready/age 진단 추가.
- 10/6: 사용자 완료 보고, 그리퍼 I/O 확인, Confluence·인수인계 작성. LAN/DDS·Goal 필드 밀림 진단, 상세 거절 로그, 실제 오류2와 복구 확인.
- 10/7: farm_interfaces 통일과 공유 원본, 통합 실행 도구, 전체 운영 문서 정리.

정확한 Rodi MAIN/STATE_TX/PICK/PLACE, 전체 Position/Joint/TCP와 그리퍼 설정을 펜던트에서 별도 백업한다. ROI와 카메라 위치·해상도를 함께 보존한다. 저널은 서버 정지 후 일관된 SQLite 백업으로 이관하며 실행 중 db파일만 복사하거나 지우지 않는다. 코드 클론만으로 현장 자산이 복원되지 않는다. JOB번호 소진 시에는 현재 프로토콜의1..65535 범위를 검토해야 한다.

기존 상세 문서와 현장 사진·첨부파일은 Confluence 인수인계 페이지에 보존한다. 이전 smartfarm_interfaces/loopback 예제보다 이 현재 운영 기준을 우선한다.

## 11. 관제와 공유할 정확한 인터페이스 원본

### action/SortBatch.action

```text
string robot_id
string task_id
string batch_id
string timestamp
---
string robot_id
string task_id
string batch_id
string result_code
int32 red_count
int32 yellow_count
string error_code
string error_message
string timestamp
---
string robot_id
string task_id
string batch_id
string phase
int32 red_count
int32 yellow_count
string timestamp
```

### msg/SorterStatus.msg

```text
string robot_id
string current_task_id
string current_batch_id
string state
bool receive_ready
bool ready
string error_code
string error_message
string boot_id
uint64 sequence
string timestamp
```
