"""Windows storage, scheduling and process helpers (no GUI dependencies)."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

VERSION = "1.4.0-win.1"
ROOT = Path(__file__).resolve().parent


def data_directory() -> Path:
    override = os.environ.get("SPARK_DATA_DIR")
    base = Path(override) if override else Path(os.environ.get("LOCALAPPDATA", Path.home())) / "SparkAssistant"
    base = base.resolve()
    base.mkdir(parents=True, exist_ok=True)
    return base


def read_json(path: Path, default=None):
    if not path.exists():
        return {} if default is None else default
    # Do not silently overwrite a damaged account database.
    with path.open(encoding="utf-8-sig") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} 必须是 JSON 对象，原文件已保留。")
    return value


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def validate_id(client_id: str):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", client_id):
        raise ValueError("客户 ID 请使用 1–64 位英文字母、数字、下划线或短横线。")


def validate_clients(clients: dict, directory: Path):
    seen_ids = set()
    seen_profiles = set()
    for cid, client in clients.items():
        validate_id(cid)
        if cid.casefold() in seen_ids:
            raise ValueError("Windows 不区分文件名大小写，请为每位客户使用不同的 ID。")
        seen_ids.add(cid.casefold())
        if not isinstance(client, dict):
            raise ValueError(f"客户 {cid} 的配置无效。")
        if not isinstance(client.get("alias", cid), str):
            raise ValueError(f"客户 {cid} 的备注名无效。")
        friends = client.get("friends", [])
        if not isinstance(friends, list) or any(not isinstance(f, str) for f in friends):
            raise ValueError(f"客户 {cid} 的好友名单无效。")
        profile = client.get("user_data_dir", f"user_data_{cid}")
        if not isinstance(profile, str):
            raise ValueError(f"客户 {cid} 的浏览器目录无效。")
        target = (directory / profile).resolve()
        if target == directory.resolve() or not target.is_relative_to(directory.resolve()):
            raise ValueError(f"客户 {cid} 的浏览器目录必须位于数据文件夹内。")
        if str(target).casefold() in seen_profiles:
            raise ValueError("不同客户不能共用浏览器目录，请分别登录。")
        seen_profiles.add(str(target).casefold())
    return clients


def worker_command(mode: str, *arguments: str) -> list[str]:
    if getattr(sys, "frozen", False):
        return [str(Path(sys.executable).with_name("SparkWorker.exe")), mode, *arguments]
    return [sys.executable, str(ROOT / "windows_worker.py"), mode, *arguments]


def autostart_command() -> str:
    if getattr(sys, "frozen", False):
        args = [sys.executable, "--background"]
    else:
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        args = [str(pythonw if pythonw.exists() else Path(sys.executable)), str(ROOT / "windows_app.py"), "--background"]
    return subprocess.list2cmdline(args)


def is_autostart_enabled() -> bool:
    if sys.platform != "win32":
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
            return bool(winreg.QueryValueEx(key, "DouyinSparkAssistant")[0])
    except FileNotFoundError:
        return False


def set_autostart(enabled: bool):
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
        if enabled:
            winreg.SetValueEx(key, "DouyinSparkAssistant", 0, winreg.REG_SZ, autostart_command())
        else:
            try:
                winreg.DeleteValue(key, "DouyinSparkAssistant")
            except FileNotFoundError:
                pass


def schedule_due(settings: dict, now: datetime) -> bool:
    if not settings.get("schedule_enabled", False):
        return False
    scheduled = settings.get("schedule_time", "09:30")
    if not isinstance(scheduled, str) or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", scheduled):
        return False
    return (settings.get("last_scheduled_date") != now.date().isoformat()
            and now.strftime("%H:%M") >= scheduled)


def configure_browser_path():
    bundled = ROOT / "browsers"
    development = ROOT / ".windows-browsers"
    if bundled.exists():
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(bundled)
    elif development.exists():
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(development))


def contain_worker_processes():
    """Keep this worker and Chromium descendants in a kill-on-close Windows Job.

    The handle deliberately lives until process exit. Windows then closes it and
    terminates remaining descendants, including after a crash or forced stop.
    """
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes

    class BasicLimits(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                    ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                    ("SchedulingClass", wintypes.DWORD)]

    class IoCounters(ctypes.Structure):
        _fields_ = [(name, ctypes.c_uint64) for name in ("ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                   "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

    class ExtendedLimits(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", BasicLimits), ("IoInfo", IoCounters),
                    ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateJobObjectW(None, None)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    limits = ExtendedLimits()
    limits.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not kernel.SetInformationJobObject(handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
        error = ctypes.WinError(ctypes.get_last_error())
        kernel.CloseHandle(handle)
        raise error
    if not kernel.AssignProcessToJobObject(handle, kernel.GetCurrentProcess()):
        error = ctypes.WinError(ctypes.get_last_error())
        kernel.CloseHandle(handle)
        raise error
    return handle
