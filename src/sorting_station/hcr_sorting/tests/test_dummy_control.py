"""Reset command behavior without sending any robot commands."""
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from rclpy.task import Future
from std_srvs.srv import Trigger
from hcr_sorting.dummy_control import DummyControl


class ResetCommandTests(unittest.TestCase):
    def setUp(self):
        self.node = DummyControl.__new__(DummyControl)
        self.node.busy = False
        self.node.reset_future = None
        self.node.reset_started = 0.0
        self.node.status = SimpleNamespace(ready=True)
        self.node.status_at = time.monotonic()
        self.node.last_error = 'old error'
        self.node.client = Mock()
        self.node.client.server_is_ready.return_value = True
        self.node.reset_client = Mock()
        self.node.reset_client.service_is_ready.return_value = True
        self.future = Future()
        self.node.reset_client.call_async.return_value = self.future
        self.node.get_logger = Mock(return_value=Mock())

    def test_success_requires_fresh_status_and_explicit_start(self):
        self.assertTrue(self.node.reset_fault())
        self.assertFalse(self.node.ready())
        self.future.set_result(Trigger.Response(success=True, message='Fault cleared'))
        self.assertIsNone(self.node.reset_future)
        self.assertIsNone(self.node.status)
        self.assertEqual(self.node.last_error, '')
        self.assertFalse(self.node.ready())
        self.node.robot_id = 'sorter_01'
        self.node.on_status(SimpleNamespace(robot_id='sorter_01', ready=True))
        self.assertTrue(self.node.ready())
        self.node.client.send_goal_async.assert_not_called()

    def test_busy_blocks_reset(self):
        self.node.busy = True
        self.assertFalse(self.node.reset_fault())
        self.node.reset_client.call_async.assert_not_called()

    def test_duplicate_reset_is_blocked(self):
        self.assertTrue(self.node.reset_fault())
        self.assertFalse(self.node.reset_fault())
        self.node.reset_client.call_async.assert_called_once()

    def test_unavailable_service_is_reported(self):
        self.node.reset_client.service_is_ready.return_value = False
        self.assertFalse(self.node.reset_fault())
        self.node.reset_client.call_async.assert_not_called()

    def test_rejection_keeps_error_status_and_allows_retry(self):
        self.node.status = SimpleNamespace(ready=False)
        status = self.node.status
        self.node.reset_fault()
        self.future.set_result(Trigger.Response(success=False, message='HCR not ready'))
        self.assertIs(self.node.status, status)
        self.assertFalse(self.node.ready())
        self.assertEqual(self.node.last_error, 'old error')
        self.node.reset_client.call_async.return_value = Future()
        self.assertTrue(self.node.reset_fault())

    def test_response_exception_is_reported(self):
        self.node.reset_fault()
        self.future.set_exception(RuntimeError('connection lost'))
        self.assertIsNone(self.node.reset_future)
        self.node.get_logger().error.assert_called_once()

    def test_timeout_and_late_response_do_not_change_status(self):
        status = self.node.status
        self.node.reset_fault()
        self.node.reset_started = time.monotonic() - 11
        self.node.check_reset_timeout()
        self.assertIsNone(self.node.reset_future)
        self.assertTrue(self.future.cancelled())
        late = Future()
        late.set_result(Trigger.Response(success=True))
        self.node.on_reset(late)
        self.assertIs(self.node.status, status)


if __name__ == '__main__':
    unittest.main()
