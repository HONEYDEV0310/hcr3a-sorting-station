# manyfarm5G 관제 통신 테스트

2026-10-29 관제팀이 안내한 연결 정보와 선별장 설정을 정리했다. 이 문서는 통신 성공 결과 보고서가 아니라 현장 시험 절차다.

## 연결 정보

| 항목 | 값 |
|---|---|
| 현장 Wi-Fi | manyfarm5G |
| 관제 유선 주소 | 192.168.0.20 |
| 관제 Zenoh TCP 포트 | 7447 |
| 선별장 접속 endpoint | tcp/192.168.0.20:7447 |
| 선별장 내부 RMW | rmw_cyclonedds_cpp |
| 선별장 내부 DDS | localhost / Domain 77 |
| HCR 유선 | PC 192.168.3.2 ↔ HCR 192.168.3.100 |

같은 Wi-Fi 이름만으로 관제 유선망 접근이 보장되지는 않는다. 관제의 실제 주소가 변경되면 config/sorting_station.json의 zenoh_endpoint도 맞춘다. HCR 유선 주소는 별도다.

## 인터넷 연결 중 준비

ROS·CycloneDDS·Zenoh 브리지·OpenCV·NumPy 설치와 farm_interfaces 빌드를 끝낸다. 이 저장소와 필요한 문서를 PC에 저장한다. 현장에서는 인터넷 없이 내부망으로 통신한다.

## 실행 순서

진행 중 작업이 없고 로봇이 복귀한 상태에서 Wi-Fi를 전환한다. GUI로 manyfarm5G에 연결하거나 이미 저장된 프로필을 사용한다.

```bash
nmcli -w 20 connection up id manyfarm5G ifname wlp2s0
nmcli -t -f NAME,DEVICE connection show --active
nc -vz -w 3 192.168.0.20 7447
```

NIC 이름은 PC마다 다르다. nc가 succeeded이면 TCP 접속 성공이다. timeout이면 현재 Wi-Fi·라우팅·관제 listen 주소·방화벽·AP 단말 격리를 관제팀과 확인한다. 성공 전에는 ROS 설정만 반복 변경하지 않는다.

선별장 저장소 루트에서:

```bash
bash start_sorting.sh
```

통합 실행기는 웹캠·서버·브리지를 함께 시작하므로 이미 실행 중이면 중복 실행하지 않는다. 별도 브리지도 추가로 켜지 않는다. 시작 화면의 Domain 77 / interface lo / 관제 endpoint를 확인한다.

다른 터미널에서 로컬 Status를 확인한다.

```bash
source /opt/ros/jazzy/setup.bash
source outputs/sorting_station/ros2/install/setup.bash
source outputs/sorting_station/launcher/ros_env.sh
ros2 topic echo /sorter_01/status --once
```

로컬 Status 출력은 선별장 내부 발행 확인이다. 외부 연결은 관제 PC에서 같은 Topic 수신을 확인해야 한다.

## 관제와 확인할 계약

| 구분 | 이름 | 타입 |
|---|---|---|
| 상태 | /sorter_01/status | farm_interfaces/msg/SorterStatus |
| 작업 | /sorter_01/sort_batch | farm_interfaces/action/SortBatch |
| 복구 | /sorter_01/reset_fault | std_srvs/srv/Trigger |

- robot_id는 sorter_01이다. 양쪽 farm_interfaces 정의를 동일하게 빌드한다.
- Status는 약 1Hz. ready=false여도 메시지 수신 시험은 가능하다. Goal은 ready=true/error_code=NONE 확인 후 보낸다.
- Goal의 robot_id/task_id/batch_id/timestamp 필드를 모두 보낸다. task_id는 매 시험 새 값을 사용한다.
- 빈 4구역 NO_COLOR가 연속 3초이면 0회 SUCCESS. 이후 한 개 운반으로 Feedback/Result를 확인한다.
- Feedback의 red_count/yellow_count는 누적값이다. 최신값으로 교체하고 Result로 최종 확정한다.
- 취소는 진행 중 한 회 운반과 HOME 복귀 후 완료된다. FAILED/CANCELED에서도 완료 수량은 보존한다.
- receive_ready는 ready와 운영자 반입 허용의 결합이다. 기본 false이며 실제 반입 가능 확인 후 --allow-receive를 사용한다.

## 관제팀에 전달할 메시지

TCP 접속을 실제 확인한 후 다음처럼 전달한다.

> 선별장 manyfarm5G 연결 후 192.168.0.20:7447 TCP 접속을 확인했습니다. 선별장 내부는 CycloneDDS / localhost / Domain 77로 실행 중입니다. /sorter_01/status (farm_interfaces/msg/SorterStatus) 수신 확인 부탁드립니다. Status 확인 후 새 task_id로 Goal → Feedback → Result 순서로 시험하겠습니다.

## 시험 기록

현장에서 날짜·PC IP·TCP 결과·관제 Status 수신·Goal 수락·Feedback·Result·취소 수량 보존·오류/복구 결과를 기록한다. 과거 HCR_ERROR_2는 로봇이 보낸 오류 번호이며 정확한 분기는 펜던트 프로그램으로 확인한다. HCR 상태 주소100의 주기 송신이 없으면 TCP 연결이 살아 있어도 ready가 되지 않는다.
