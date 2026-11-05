# farm_interfaces

HCR 선별장용 `action/SortBatch.action`, `msg/SorterStatus.msg`를 제공한다.
관제와 선별장은 같은 정의로 빌드해야 한다. 계약 및 보류 항목은
`docs/INTERFACES.md`, 실행은 `src/sorting_station/hcr_sorting/README.md` 참조.
수확 SO101의 메시지/제어 구현을 포함하지 않는다.

## 관제와 원본 공유 (2026-10-07)

`smartfarm_interfaces`에서 패키지 이름만 변경했으며 다음 두 파일은 바이트 단위로 동일하다.

- `action/SortBatch.action`
- `msg/SorterStatus.msg`

관제에 기존 `farm_interfaces` 패키지가 있다면 이 두 파일을 추가하고
기존 `rosidl_generate_interfaces` 목록에 등록한다. 다른 예찰·수확 인터페이스를 덮어쓰지 않는다.
양쪽을 재빌드한 뒤 새 터미널에서 각 workspace의 `install/setup.bash`를 source한다.
기존 실행 중인 프로세스는 자동 전환되지 않으므로 관제와 작업 종료·전환 시점을 맞춰 재시작한다.

선별장 빌드:

```bash
bash src/sorting_station/hcr/build_sorter.sh
source /opt/ros/jazzy/setup.bash
source outputs/sorting_station/ros2/install/setup.bash
ros2 interface show farm_interfaces/action/SortBatch
ros2 interface show farm_interfaces/msg/SorterStatus
```
