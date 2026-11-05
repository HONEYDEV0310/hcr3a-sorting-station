"""Start the webcam, ROS server and optional Zenoh bridge; never send a Goal."""
import argparse
import fcntl
import ipaddress
import json
import os
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
RESET_ENV = ('CYCLONEDDS_URI', 'ROS_STATIC_PEERS', 'ROS_DISCOVERY_SERVER',
             'ROS_LOCALHOST_ONLY', 'FASTRTPS_DEFAULT_PROFILES_FILE',
             'FASTDDS_DEFAULT_PROFILES_FILE')


def load_config(path):
    config = json.loads(path.read_text())
    if type(config['receive_enabled']) is not bool:
        raise ValueError('receive_enabled must be true or false')
    if type(config['ros_domain_id']) is not int or not 0 <= config['ros_domain_id'] <= 232:
        raise ValueError('Invalid ROS domain')
    if type(config['modbus_port']) is not int or not 1 <= config['modbus_port'] <= 65535:
        raise ValueError('Invalid Modbus port')
    for key in ('modbus_host', 'modbus_peer'):
        ipaddress.IPv4Address(config[key])
    if config['camera'] is not None and type(config['camera']) not in (str, int):
        raise ValueError('camera must be null, an index or a device path')
    endpoint = config.get('zenoh_endpoint')
    if endpoint is not None:
        if not isinstance(endpoint, str) or not endpoint.startswith('tcp/'):
            raise ValueError('zenoh_endpoint must be tcp/<host>:<port> or null')
        host, separator, port = endpoint[4:].rpartition(':')
        if not host or not separator or not port.isdigit() or not 1 <= int(port) <= 65535:
            raise ValueError('zenoh_endpoint must be tcp/<host>:<port> or null')
    return config


def ros_environment(config, check_network=True):
    xml_path = (ROOT / config['dds_config']).resolve()
    tree = ET.parse(xml_path)
    interfaces = tree.findall('.//{*}NetworkInterface')
    if len(interfaces) != 1:
        raise ValueError('DDS XML must specify one NetworkInterface')
    interface = interfaces[0].get('name')
    if interface is None and interfaces[0].get('address') == '127.0.0.1':
        interface = 'lo'
    if not interface:
        raise ValueError('DDS XML must specify an interface name or address 127.0.0.1')
    if config.get('zenoh_endpoint') and interface != 'lo':
        raise ValueError('Zenoh bridge requires a loopback DDS interface')
    peers = [p.get('address') or p.get('Address') for p in tree.findall('.//{*}Peer')]
    local_ip = None
    if check_network:
        result = subprocess.run(['ip', '-j', '-4', 'addr', 'show', 'dev', interface],
                                capture_output=True, text=True, check=True)
        for device in json.loads(result.stdout):
            for address in device.get('addr_info', []):
                if address.get('family') == 'inet':
                    local_ip = address['local']
                    break
        if local_ip is None:
            raise ValueError(f'{interface}: IPv4 address missing')
    values = {
        'ROS_DISTRO': 'jazzy',
        'ROS_DOMAIN_ID': str(config['ros_domain_id']),
        'RMW_IMPLEMENTATION': 'rmw_cyclonedds_cpp',
        'CYCLONEDDS_URI': xml_path.as_uri(),
        'ROS_AUTOMATIC_DISCOVERY_RANGE': 'LOCALHOST' if interface == 'lo' else 'SUBNET',
    }
    if not config.get('zenoh_endpoint'):
        # Legacy direct DDS mode: include this PC for local dummy discovery.
        values['ROS_STATIC_PEERS'] = ';'.join(dict.fromkeys([p for p in peers if p] + ([local_ip] if local_ip else [])))
    return values, interface


def process_environment(values, inherited=None):
    env = dict(os.environ if inherited is None else inherited)
    for key in RESET_ENV:
        env.pop(key, None)
    env.update(values)
    return env


def environment_script(values):
    return ('unset ' + ' '.join(RESET_ENV) + '\n' +
            '\n'.join(f'export {key}={shlex.quote(value)}' for key, value in values.items()) + '\n')


def commands(config, values):
    camera = ['bash', str(ROOT / 'src/sorting_station/hcr/run_webcam_preview.sh')]
    if config['camera'] is not None:
        camera += ['--camera', str(config['camera'])]
    server = ['sudo', '-n', '-E', 'env']
    for key in RESET_ENV:
        server += ['-u', key]
    server += [f'{k}={v}' for k, v in values.items()]
    server += ['bash', str(ROOT / 'src/sorting_station/hcr/run_sorter.sh'), '--ros-args',
               '-p', f'modbus_host:={config["modbus_host"]}',
               '-p', f'modbus_port:={config["modbus_port"]}',
               '-p', f'modbus_peer:={config["modbus_peer"]}',
               '-p', f'receive_enabled:={str(config["receive_enabled"]).lower()}']
    command_list = [('webcam', camera), ('server', server)]
    if config.get('zenoh_endpoint'):
        bridge = ['zenoh-bridge-ros2dds', '--domain', str(config['ros_domain_id']),
                  '--ros-localhost-only', '--no-multicast-scouting',
                  '-e', config['zenoh_endpoint']]
        command_list.insert(0, ('bridge', bridge))
    return command_list


def stop_process(process):
    """Signal only this launcher's dedicated child process group, including sudo."""
    if process.poll() is not None:
        return
    for sig, timeout in ((signal.SIGINT, 8), (signal.SIGTERM, 3), (signal.SIGKILL, 3)):
        try:
            os.killpg(process.pid, sig)
        except PermissionError:
            subprocess.run(['sudo', '-n', 'kill', f'-{sig.value}', '--', f'-{process.pid}'],
                           check=True, timeout=5)
        except ProcessLookupError:
            return
        try:
            process.wait(timeout=timeout)
            return
        except subprocess.TimeoutExpired:
            pass
    raise RuntimeError(f'Could not stop child process {process.pid}')


def show_status(path, previous):
    try:
        if time.time() - path.stat().st_mtime > 2:
            signature = ('stale',)
            message = '서버 상태 갱신 대기 중…'
        else:
            data = json.loads(path.read_text())
            signature = tuple(data.get(k) for k in ('phase', 'ready', 'camera_ready', 'robot_connected', 'error'))
            message = (f'상태={data.get("phase")} 준비={data.get("ready")} '
                       f'카메라={data.get("camera_ready")} HCR연결={data.get("robot_connected")} '
                       f'오류={data.get("error")}')
    except (OSError, ValueError):
        signature, message = ('waiting',), '서버 상태 생성 대기 중…'
    if signature != previous:
        print(message, flush=True)
    return signature


def supervise(command_list, env, log_dir, runtime_path):
    children, handles = [], []
    try:
        for name, command in command_list:
            handle = (log_dir / f'{name}.log').open('w')
            handles.append(handle)
            process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=handle,
                                       stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                       process_group=0)
            children.append((name, process))
        print('실행 중: ' + ', '.join(name for name, _ in children) +
              '. 종료: 작업 완료 후 Ctrl+C. 이 종료는 물리 비상정지가 아닙니다.', flush=True)
        previous = None
        last_sudo_refresh = time.monotonic()
        while True:
            for name, process in children:
                code = process.poll()
                if code is not None:
                    print(f'{name} 종료(코드 {code}). 함께 실행한 프로그램을 종료합니다.', flush=True)
                    log = log_dir / f'{name}.log'
                    print('\n'.join(log.read_text(errors='replace').splitlines()[-15:]), flush=True)
                    return code if code else 0
            previous = show_status(runtime_path, previous)
            if time.monotonic() - last_sudo_refresh >= 60:
                # Keep authentication available to stop our root server on exit.
                subprocess.run(['sudo', '-n', '-v'], check=True)
                last_sudo_refresh = time.monotonic()
            time.sleep(.25)
    except KeyboardInterrupt:
        return 130
    finally:
        # Stop server first so it clears its PC registers before camera disappears.
        errors = []
        for name, process in reversed(children):
            try:
                stop_process(process)
            except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
                errors.append(f'{name}: {exc}')
        for handle in handles:
            handle.close()
        if errors:
            raise RuntimeError('; '.join(errors))


def main():
    parser = argparse.ArgumentParser(description='웹캠·HCR 서버·Zenoh 브리지 함께 실행 (Goal 자동 전송 없음)')
    parser.add_argument('--config', type=Path, default=ROOT / 'config/sorting_station.json')
    parser.add_argument('--camera', help='USB 카메라 index 또는 /dev/v4l/by-id 경로')
    parser.add_argument('--allow-receive', action='store_true', help='운영자가 반입 가능을 확인한 경우 반입 허용')
    parser.add_argument('--dry-run', action='store_true', help='하드웨어 접속·sudo 없이 설정과 실행 명령 확인')
    parser.add_argument('--dummy', action='store_true', help='서버를 추가 실행하지 않고 같은 설정의 더미 관제 실행')
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error('sudo 없이 실행하세요. 웹캠은 일반 사용자로 실행하고 서버만 권한을 요청합니다.')
    config = load_config(args.config)
    if args.camera is not None:
        config['camera'] = args.camera
    if args.allow_receive:
        config['receive_enabled'] = True
    values, interface = ros_environment(config, not args.dry_run)
    env = process_environment(values)
    print(f'ROS={values["RMW_IMPLEMENTATION"]} / interface={interface} / Domain={values["ROS_DOMAIN_ID"]}', flush=True)
    if config.get('zenoh_endpoint'):
        print(f'관제 연결: Zenoh {config["zenoh_endpoint"]} (PC 내부 DDS는 localhost)', flush=True)
    if not args.dummy:
        print(f'반입 허용={config["receive_enabled"]}. 실행만으로 선별 작업을 시작하지 않습니다.', flush=True)
    command_list = commands(config, values)
    if args.dummy:
        command_list = [('dummy', ['bash', str(ROOT / 'src/sorting_station/hcr/run_dummy_control.sh')])]
    if args.dry_run:
        for name, command in command_list:
            print(f'{name}: {shlex.join(command)}')
        return 0
    if not (ROOT / 'outputs/sorting_station/ros2/install/farm_interfaces').is_dir():
        raise ValueError('farm_interfaces 빌드 필요: bash src/sorting_station/hcr/build_sorter.sh')
    if args.dummy:
        return subprocess.call(command_list[0][1], cwd=ROOT, env=env)
    if config.get('zenoh_endpoint') and shutil.which('zenoh-bridge-ros2dds') is None:
        raise ValueError('zenoh-bridge-ros2dds 설치 필요. docs/hcr3a/09_ZENOH_START.md 참고')
    if not (env.get('DISPLAY') or env.get('WAYLAND_DISPLAY')):
        raise ValueError('카메라 GUI를 표시할 데스크탑 터미널에서 실행하세요.')
    run_dir = ROOT / 'outputs/sorting_station/launcher'
    run_dir.mkdir(parents=True, exist_ok=True)
    with (run_dir / 'station.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('이미 통합 실행기가 실행 중입니다.')
        # Also detect servers started manually. Do not kill or replace them.
        port = config['modbus_port']
        result = subprocess.run(['ss', '-H', '-ltn', f'sport = :{port}'],
                                capture_output=True, text=True, check=True)
        if result.stdout.strip():
            raise ValueError(f'포트 {port}가 사용 중입니다. 기존 서버의 작업 종료 후 종료하세요.')
        subprocess.run(['sudo', '-v'], check=True)
        if config.get('zenoh_endpoint'):
            subprocess.run(['sudo', '-n', 'ip', 'link', 'set', 'lo', 'multicast', 'on'], check=True)
        log_dir = run_dir / time.strftime('%Y%m%d_%H%M%S')
        log_dir.mkdir()
        # Export the exact same settings for recovery/dummy control in another terminal.
        (run_dir / 'ros_env.sh').write_text(environment_script(values))
        (log_dir / 'settings.json').write_text(json.dumps(config, ensure_ascii=False, indent=2))
        print(f'로그: {log_dir}', flush=True)
        return supervise(command_list, env, log_dir, ROOT / 'outputs/sorting_station/hcr_runtime/runtime.json')


def handle_signal(signum, frame):
    raise KeyboardInterrupt


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, handle_signal)
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError, ET.ParseError) as exc:
        print(f'실행 실패: {exc}', file=sys.stderr)
        sys.exit(1)
