"""Interactive central-control substitute. Sending a goal can move real hardware."""
import argparse
from datetime import datetime, timezone
import select
import sys
import time
import uuid

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from farm_interfaces.action import SortBatch
from farm_interfaces.msg import SorterStatus
from std_srvs.srv import Trigger


class DummyControl(Node):
    def __init__(self, robot_id='sorter_01'):
        super().__init__('dummy_sorter_control')
        self.robot_id = robot_id
        self.status = None
        self.status_at = 0.0
        self.busy = False
        self.goal = None
        self.cancel_requested = False
        self.cancel_sent = False
        self.last_result = None
        self.last_feedback = None
        self.last_error = ''
        self.reset_future = None
        self.reset_started = 0.0
        self.reset_client = self.create_client(Trigger, f'/{robot_id}/reset_fault')
        self.reset_timer = self.create_timer(0.5, self.check_reset_timeout)
        self.client = ActionClient(self, SortBatch, f'/{robot_id}/sort_batch')
        self.subscription = self.create_subscription(
            SorterStatus, f'/{robot_id}/status', self.on_status, 10)

    def on_status(self, message):
        if message.robot_id == self.robot_id:
            self.status, self.status_at = message, time.monotonic()

    def ready(self):
        return bool(not self.busy and self.reset_future is None and self.status and self.status.ready
                    and time.monotonic() - self.status_at < 3.0
                    and self.client.server_is_ready())

    def report(self):
        if not self.status:
            return '아직 status를 받지 못했습니다. 실행기/ROS_DOMAIN_ID를 확인하세요.'
        s = self.status
        return (f'state={s.state} ready={s.ready} status_age={time.monotonic()-self.status_at:.1f}s '
                f'task={s.current_task_id} error={s.error_code} local_active={self.busy}')

    def reset_fault(self):
        if self.busy:
            self.get_logger().warning('초기화 불가: 작업 결과를 기다리는 중입니다. 최종 Result를 확인하세요.')
            return False
        if self.reset_future is not None:
            self.get_logger().warning('이미 에러 초기화 응답을 기다리고 있습니다.')
            return False
        if not self.reset_client.service_is_ready():
            self.get_logger().warning('초기화 서비스에 연결되지 않았습니다. 실행기와 ROS_DOMAIN_ID를 확인하세요.')
            return False
        self.reset_started = time.monotonic()
        self.reset_future = self.reset_client.call_async(Trigger.Request())
        self.reset_future.add_done_callback(self.on_reset)
        self.get_logger().info('에러 초기화 요청 전송. 로봇이 복귀·정지하고 카메라가 정상인지 확인하세요.')
        return True

    def on_reset(self, future):
        if future is not self.reset_future:
            return
        self.reset_future = None
        try:
            response = future.result()
            if response.success:
                # Require a new server status after reset, not a cached READY.
                self.status = None
                self.status_at = 0.0
                self.last_error = ''
                self.get_logger().info('에러 초기화 성공. p로 ready=True와 error=NONE을 확인한 뒤 s로 새 작업을 시작하세요.')
            else:
                self.get_logger().warning(
                    '에러 초기화 거절: 카메라 정상, HCR_STATE=1, HCR_ERROR=0, '
                    '진행 중 작업 없음이 필요합니다. 원인을 해결한 뒤 r을 다시 입력하세요. '
                    + response.message)
        except Exception as exc:
            self.get_logger().error(f'에러 초기화 응답 확인 실패: {exc}. p로 서버 상태를 확인하세요.')

    def check_reset_timeout(self):
        if self.reset_future is not None and time.monotonic() - self.reset_started >= 10.0:
            future, self.reset_future = self.reset_future, None
            future.cancel()
            self.get_logger().warning('에러 초기화 응답 시간 초과. 처리 여부는 p로 확인하세요. 자동 재시작하지 않습니다.')

    def start(self, task_id=None, batch_id=None):
        if not self.ready():
            self.get_logger().warning('시작 불가: ' + self.report())
            return False
        suffix = uuid.uuid4().hex
        goal = SortBatch.Goal(robot_id=self.robot_id,
                              task_id=task_id or f'DUMMY_{suffix}',
                              batch_id=batch_id or f'BATCH_{suffix}',
                              timestamp=datetime.now(timezone.utc).isoformat())
        self.busy = True
        self.goal = None
        self.cancel_requested = self.cancel_sent = False
        self.last_result = self.last_feedback = None
        self.last_error = ''
        self.get_logger().info(f'Goal 전송 task={goal.task_id} batch={goal.batch_id}')
        self.client.send_goal_async(goal, feedback_callback=self.on_feedback).add_done_callback(self.on_goal)
        return True

    def on_goal(self, future):
        try:
            self.goal = future.result()
            if not self.goal.accepted:
                self.busy = False
                self.last_error = 'GOAL_REJECTED'
                self.get_logger().warning('Goal 거절됨. 자동 재전송하지 않습니다.')
                return
            self.get_logger().info('Goal 수락됨')
            self.goal.get_result_async().add_done_callback(self.on_result)
            if self.cancel_requested:
                self.cancel()
        except Exception as exc:
            self.unknown(exc)

    def on_feedback(self, message):
        f = message.feedback
        key = (f.phase, f.red_count, f.yellow_count)
        if key != self.last_feedback:
            self.get_logger().info(f'{f.phase}: 빨강={f.red_count} 노랑={f.yellow_count} 합계={f.red_count+f.yellow_count}')
        self.last_feedback = key

    def on_result(self, future):
        try:
            result = future.result().result
            self.last_result = result
            self.busy = False
            self.get_logger().info(
                f'{result.result_code}: 빨강={result.red_count} 노랑={result.yellow_count} '
                f'총={result.red_count+result.yellow_count} error={result.error_code} {result.error_message}')
        except Exception as exc:
            self.unknown(exc)

    def unknown(self, exc):
        # An uncertain request must never be silently retried as a fresh task.
        self.last_error = str(exc)
        self.get_logger().error(f'요청 결과 불확실: {exc}. 새 작업을 차단합니다. 실제 상태를 확인하세요.')

    def cancel(self):
        if not self.busy:
            return False
        self.cancel_requested = True
        if self.goal is not None and self.goal.accepted and not self.cancel_sent:
            self.cancel_sent = True
            self.goal.cancel_goal_async().add_done_callback(self.on_cancel)
        return True

    def on_cancel(self, future):
        try:
            response = future.result()
            if response.goals_canceling:
                self.get_logger().info('취소 수락: 진행 중 1회 완료 및 복귀 후 최종 Result를 기다립니다.')
            else:
                self.cancel_sent = False
                self.get_logger().warning('취소 거절 또는 이미 종료됨. Result를 기다립니다.')
        except Exception as exc:
            self.unknown(exc)


def main(args=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--robot-id', default='sorter_01')
    opts, ros_args = parser.parse_known_args(args)
    rclpy.init(args=ros_args)
    node = DummyControl(opts.robot_id)
    print('더미 관제: s=시작(하역 완료·운송로봇 이격 확인 후), p=상태, c=취소, r=에러 초기화, q=종료', flush=True)
    print('실제 실행기에 연결하면 s는 실제 로봇 작업을 요청합니다. 취소는 비상정지가 아닙니다.', flush=True)
    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.1)
            if not select.select([sys.stdin], [], [], 0)[0]:
                continue
            line = sys.stdin.readline()
            if not line:
                node.get_logger().warning('입력 종료. 활성 작업은 자동 정지되지 않습니다.')
                break
            command = line.strip().lower()
            if command == 's': node.start()
            elif command == 'p': print(node.report(), flush=True)
            elif command == 'c': node.cancel()
            elif command == 'r': node.reset_fault()
            elif command == 'q':
                if node.busy:
                    print('진행 중입니다. c로 취소하고 최종 Result 후 q를 입력하세요.', flush=True)
                else: break
    except KeyboardInterrupt:
        print('관제 종료. 실행 중인 로봇 작업은 자동 정지되지 않습니다.', flush=True)
    finally:
        node.reset_client.destroy()
        node.client.destroy()
        node.destroy_node()
        if rclpy.ok(): rclpy.shutdown()


if __name__ == '__main__':
    main()
