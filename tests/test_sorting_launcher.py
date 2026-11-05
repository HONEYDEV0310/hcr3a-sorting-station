"""Launcher lifecycle tests use disposable Python children, never ROS/hardware."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parents[1] / 'scripts/start_sorting_station.py'
spec = importlib.util.spec_from_file_location('sorting_launcher', MODULE_PATH)
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


class LauncherTests(unittest.TestCase):
    def config(self):
        return launcher.load_config(launcher.ROOT / 'config/sorting_station.json')

    def test_zenoh_environment_clears_old_network_settings(self):
        with patch.object(launcher.subprocess, 'run') as run:
            run.return_value.stdout = json.dumps([{'addr_info': [{'family': 'inet', 'local': '127.0.0.1'}]}])
            values, interface = launcher.ros_environment(self.config())
        self.assertEqual(interface, 'lo')
        self.assertTrue(values['CYCLONEDDS_URI'].endswith('/config/cyclonedds_zenoh.xml'))
        self.assertEqual(values['ROS_DOMAIN_ID'], '77')
        self.assertEqual(values['ROS_AUTOMATIC_DISCOVERY_RANGE'], 'LOCALHOST')
        inherited = {key: 'old-setting' for key in launcher.RESET_ENV}
        inherited['RMW_IMPLEMENTATION'] = 'rmw_fastrtps_cpp'
        env = launcher.process_environment(values, inherited)
        self.assertEqual(env['RMW_IMPLEMENTATION'], 'rmw_cyclonedds_cpp')
        for key in set(launcher.RESET_ENV) - set(values):
            self.assertNotIn(key, env)
        self.assertEqual(env['CYCLONEDDS_URI'], values['CYCLONEDDS_URI'])

    def test_zenoh_requires_local_dds(self):
        config = self.config()
        config['dds_config'] = 'config/cyclonedds_lan.xml'
        with self.assertRaisesRegex(ValueError, 'loopback'):
            launcher.ros_environment(config, False)

    def test_legacy_direct_dds_settings(self):
        config = self.config()
        config.pop('zenoh_endpoint')
        config['dds_config'] = 'config/cyclonedds_lan.xml'
        with patch.object(launcher.subprocess, 'run') as run:
            run.return_value.stdout = json.dumps([{'addr_info': [{'family': 'inet', 'local': '192.168.0.42'}]}])
            values, interface = launcher.ros_environment(config)
        self.assertEqual(interface, 'wlp2s0')
        self.assertEqual(values['ROS_STATIC_PEERS'], '192.168.0.20;192.168.0.42')
        self.assertEqual([name for name, _ in launcher.commands(config, values)], ['webcam', 'server'])

    def test_missing_ipv4_fails_before_launch(self):
        with patch.object(launcher.subprocess, 'run') as run:
            run.return_value.stdout = '[{"addr_info": []}]'
            with self.assertRaisesRegex(ValueError, 'IPv4'):
                launcher.ros_environment(self.config())

    def test_camera_stays_unprivileged_and_receive_default_is_false(self):
        config = self.config()
        config['camera'] = '/dev/v4l/by-id/camera with spaces'
        values, _ = launcher.ros_environment(config, False)
        bridge, camera, server = launcher.commands(config, values)
        self.assertEqual(bridge[1], ['zenoh-bridge-ros2dds', '--domain', '77',
                                   '--ros-localhost-only', '--no-multicast-scouting',
                                   '-e', 'tcp/192.168.0.20:7447'])
        self.assertEqual(camera[1][0], 'bash')
        self.assertEqual(camera[1][-1], config['camera'])
        self.assertEqual(server[1][0], 'sudo')
        self.assertIn('receive_enabled:=false', server[1])
        self.assertNotIn('send_goal', ' '.join(server[1]))
        for key in launcher.RESET_ENV:
            self.assertIn(key, server[1])

    def test_recovery_shell_uses_identical_environment(self):
        import subprocess
        values, _ = launcher.ros_environment(self.config(), False)
        script = launcher.environment_script(values)
        script += '\n/usr/bin/python3 -c "import json, os; print(json.dumps(dict(os.environ)))"'
        old = {key: 'old-setting' for key in launcher.RESET_ENV}
        result = subprocess.run(['bash', '-c', script], env=old, text=True,
                                capture_output=True, check=True)
        env = json.loads(result.stdout)
        for key, value in values.items():
            self.assertEqual(env[key], value)
        for key in set(launcher.RESET_ENV) - set(values):
            self.assertNotIn(key, env)

    def test_dummy_dry_run_does_not_start_another_bridge(self):
        with patch.object(launcher.os, 'geteuid', return_value=1000), \
             patch.object(sys, 'argv', ['start_sorting_station.py', '--dummy', '--dry-run']), \
             patch('builtins.print') as output, \
             patch.object(launcher.subprocess, 'Popen') as popen:
            self.assertEqual(launcher.main(), 0)
        lines = [' '.join(str(arg) for arg in call.args) for call in output.call_args_list]
        commands = [line for line in lines if line.startswith(('bridge:', 'webcam:', 'server:', 'dummy:'))]
        self.assertEqual(len(commands), 1)
        self.assertTrue(commands[0].startswith('dummy:'))
        popen.assert_not_called()

    def test_invalid_boolean_config_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'config.json'
            config = self.config(); config['receive_enabled'] = 'false'
            p.write_text(json.dumps(config))
            with self.assertRaisesRegex(ValueError, 'receive_enabled'):
                launcher.load_config(p)

    def test_invalid_zenoh_endpoint_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'config.json'
            for endpoint in ('udp/192.168.0.20:7447', 'tcp/192.168.0.20', 'tcp/host:99999', 77):
                with self.subTest(endpoint=endpoint):
                    config = self.config(); config['zenoh_endpoint'] = endpoint
                    path.write_text(json.dumps(config))
                    with self.assertRaisesRegex(ValueError, 'zenoh_endpoint'):
                        launcher.load_config(path)

    def test_child_failure_stops_and_reaps_the_other_child(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            processes = []
            real_popen = launcher.subprocess.Popen
            def record(*args, **kwargs):
                p = real_popen(*args, **kwargs); processes.append(p); return p
            commands = [('webcam', [sys.executable, '-c', 'import time; time.sleep(30)']),
                        ('server', [sys.executable, '-c', 'import time; time.sleep(30)']),
                        ('bridge', [sys.executable, '-c', 'import sys,time; time.sleep(.1); sys.exit(7)'])]
            with patch.object(launcher.subprocess, 'Popen', side_effect=record):
                code = launcher.supervise(commands, os.environ.copy(), root, root / 'missing.json')
            self.assertEqual(code, 7)
            self.assertTrue(all(p.poll() is not None for p in processes))

    def test_partial_start_failure_cleans_up_started_child(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            processes = []
            real_popen = launcher.subprocess.Popen
            def record(*args, **kwargs):
                p = real_popen(*args, **kwargs); processes.append(p); return p
            commands = [('webcam', [sys.executable, '-c', 'import time; time.sleep(30)']),
                        ('server', ['/missing/sorting-launcher-test-program'])]
            with patch.object(launcher.subprocess, 'Popen', side_effect=record):
                with self.assertRaises(FileNotFoundError):
                    launcher.supervise(commands, os.environ.copy(), root, root / 'missing.json')
            self.assertTrue(all(p.poll() is not None for p in processes))

    def test_interrupt_stops_both_dedicated_children(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            processes = []
            real_popen = launcher.subprocess.Popen
            def record(*args, **kwargs):
                p = real_popen(*args, **kwargs); processes.append(p); return p
            commands = [(name, [sys.executable, '-c', 'import time; time.sleep(30)'])
                        for name in ('webcam', 'server')]
            with patch.object(launcher.subprocess, 'Popen', side_effect=record), \
                 patch.object(launcher, 'show_status', side_effect=KeyboardInterrupt):
                code = launcher.supervise(commands, os.environ.copy(), root, root / 'missing.json')
            self.assertEqual(code, 130)
            self.assertTrue(all(p.poll() is not None for p in processes))


if __name__ == '__main__':
    unittest.main()
