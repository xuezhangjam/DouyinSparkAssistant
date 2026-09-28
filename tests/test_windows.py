import ctypes
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from windows_core import read_json, schedule_due, validate_clients, validate_id, worker_command, write_json
from windows_app import MainWindow, TaskController


class StorageTests(unittest.TestCase):
    def test_unicode_roundtrip_and_corruption_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "clients.json"
            write_json(path, {"client_001": {"alias": "中文客户 🔥"}})
            self.assertEqual(read_json(path)["client_001"]["alias"], "中文客户 🔥")
            path.write_text("broken", encoding="utf-8")
            with self.assertRaises(ValueError):
                read_json(path)
            self.assertEqual(path.read_text(), "broken")

    def test_invalid_document_and_profile_escape_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            path = directory / "clients.json"
            path.write_text("[]")
            with self.assertRaises(ValueError):
                read_json(path)
            for profile in ("../outside", str(directory), str(directory.parent / "outside")):
                with self.assertRaises(ValueError):
                    validate_clients({"client_1": {"user_data_dir": profile}}, directory)
            with self.assertRaises(ValueError):
                validate_clients({"client_1": {"friends": "not a list"}}, directory)
            validate_clients({"client_1": {"user_data_dir": "user_data_client_1", "friends": ["好友"]}}, directory)

    def test_client_ids(self):
        for cid in ("../test", "a/b", "a\\b", "", "a" * 65):
            with self.assertRaises(ValueError):
                validate_id(cid)
        validate_id("client_001-A")

    def test_windows_profile_collisions_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                validate_clients({"Client_A": {}, "client_a": {}}, Path(temp))
            with self.assertRaises(ValueError):
                validate_clients({"a": {"user_data_dir": "same"}, "b": {"user_data_dir": "same"}}, Path(temp))

    def test_frozen_command_does_not_start_gui_recursively(self):
        with patch.object(sys, "frozen", True, create=True), patch.object(sys, "executable", str(ROOT / "dist" / "SparkAssistant.exe")):
            command = worker_command("run", "client_001")
        self.assertEqual(Path(command[0]).name, "SparkWorker.exe")
        self.assertEqual(command[1:], ["run", "client_001"])


class ScheduleTests(unittest.TestCase):
    def test_daily_and_catchup(self):
        settings = {"schedule_enabled": True, "schedule_time": "09:30"}
        self.assertFalse(schedule_due(settings, datetime(2026, 9, 27, 9, 29)))
        self.assertTrue(schedule_due(settings, datetime(2026, 9, 27, 9, 30)))
        self.assertTrue(schedule_due(settings, datetime(2026, 9, 27, 23, 0)))
        settings["last_scheduled_date"] = "2026-09-27"
        self.assertFalse(schedule_due(settings, datetime(2026, 9, 27, 23, 0)))
        self.assertTrue(schedule_due(settings, datetime(2026, 9, 28, 10, 0)))
        settings["schedule_enabled"] = False
        self.assertFalse(schedule_due(settings, datetime(2026, 9, 28, 10, 0)))

    def test_invalid_time_does_not_fire(self):
        for invalid in ("25:00", "9:30", "09:60", None, [], ""):
            self.assertFalse(schedule_due({"schedule_enabled": True, "schedule_time": invalid}, datetime.now()))


class QtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def wait_until(self, condition, timeout=10):
        end = time.monotonic() + timeout
        while not condition() and time.monotonic() < end:
            self.app.processEvents()
            time.sleep(0.01)
        self.assertTrue(condition(), "Timed out waiting for Qt event")

    def test_controller_unicode_progress_and_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            controller = TaskController(Path(temp))
            logs, progress, completed = [], [], []
            controller.log.connect(logs.append)
            controller.progress.connect(progress.append)
            controller.completed.connect(completed.append)
            script = "import sys; print('中文 🔥'); print('SPARK_PROGRESS:{\"percent\": 42, \"text\": \"测试\"}'); sys.exit(2)"
            with patch("windows_app.worker_command", return_value=[sys.executable, "-X", "utf8", "-c", script]):
                self.assertTrue(controller.start([("run", "client_001", "客户")]))
                self.assertFalse(controller.start([("run", "client_001", "重复")]))
                self.wait_until(lambda: not controller.busy)
            self.assertTrue(any("中文 🔥" in line for line in logs))
            self.assertTrue(any(value.get("percent") == 42 for value in progress))
            self.assertEqual(controller.failed, 1)
            self.assertIn("需要处理", completed[-1])

    def test_missing_worker_recovers_controls(self):
        with tempfile.TemporaryDirectory() as temp:
            controller = TaskController(Path(temp))
            with patch("windows_app.worker_command", return_value=[str(Path(temp) / "missing.exe")]):
                controller.start([("check", "", "check")])
                self.wait_until(lambda: not controller.busy)
            self.assertEqual(controller.failed, 1)
            self.assertIsNone(controller.process)

    def test_stop_clears_queue_during_delay(self):
        with tempfile.TemporaryDirectory() as temp:
            controller = TaskController(Path(temp))
            with patch("windows_app.worker_command", return_value=[sys.executable, "-c", "print('done')"]):
                controller.start([("check", "", "one"), ("check", "", "two")])
                self.wait_until(lambda: controller.next_timer.isActive())
                controller.stop()
            self.assertFalse(controller.busy)
            self.assertFalse(controller.queue)
            self.assertFalse(controller.next_timer.isActive())
            self.assertEqual(controller.index, 1)

    @unittest.skipUnless(sys.platform == "win32", "Windows Job Object test")
    def test_stop_kills_owned_child_process(self):
        with tempfile.TemporaryDirectory() as temp:
            script = Path(temp) / "worker.py"
            script.write_text(
                "import sys, subprocess, time\n"
                f"sys.path.insert(0, {str(ROOT)!r})\n"
                "from windows_core import contain_worker_processes\n"
                "job = contain_worker_processes()\n"
                "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
                "print('CHILD:' + str(child.pid), flush=True)\n"
                "time.sleep(60)\n", encoding="utf-8")
            controller = TaskController(Path(temp))
            logs = []
            controller.log.connect(logs.append)
            with patch("windows_app.worker_command", return_value=[sys.executable, str(script)]):
                controller.start([("check", "", "cancel")])
                self.wait_until(lambda: any(line.startswith("CHILD:") for line in logs))
                pid = int(next(line[6:] for line in logs if line.startswith("CHILD:")))
                kernel = ctypes.WinDLL("kernel32", use_last_error=True)
                kernel.OpenProcess.restype = ctypes.c_void_p
                kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
                kernel.CloseHandle.argtypes = [ctypes.c_void_p]
                handle = kernel.OpenProcess(0x100000, False, pid)
                self.assertTrue(handle)
                try:
                    controller.stop()
                    self.wait_until(lambda: not controller.busy)
                    self.assertEqual(kernel.WaitForSingleObject(handle, 5000), 0)
                finally:
                    kernel.CloseHandle(handle)
            self.assertTrue(controller.cancelled)

    def test_ui_crud_schedule_once_and_busy_guard(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            window = MainWindow(directory)
            window.tray.hide()
            window.timer.stop()
            self.assertTrue(window.test.isChecked())
            self.assertFalse(window.run_button.isEnabled())
            self.assertTrue(window.save_clients({"client_001": {"alias": "测试客户", "friends": ["好友"], "status": "active"}}))
            window.refresh("client_001")
            self.assertTrue(window.run_button.isEnabled())
            window.toggle_client()
            self.assertEqual(read_json(directory / "clients.json")["client_001"]["status"], "inactive")
            window.toggle_client()
            window.settings.update(schedule_enabled=True, schedule_time="00:00")
            with patch.object(window.controller, "start", return_value=True) as start:
                window.controller.busy = True
                window.check_schedule()
                start.assert_not_called()
                window.controller.busy = False
                window.check_schedule()
                window.check_schedule()
                self.assertEqual(start.call_count, 1)
                self.assertEqual(start.call_args.args[1:], (True, False))
            self.assertEqual(read_json(directory / "settings.json")["last_scheduled_date"], datetime.now().date().isoformat())
            self.assertFalse(schedule_due(read_json(directory / "settings.json"), datetime.now()))
            window.hide()
            for handler in window.logger.handlers[:]:
                handler.close()
                window.logger.removeHandler(handler)
            window.deleteLater()
            self.app.processEvents()


if __name__ == "__main__":
    unittest.main()
