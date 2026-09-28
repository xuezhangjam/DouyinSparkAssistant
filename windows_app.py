"""Native Windows desktop application for Douyin Spark Assistant."""
from __future__ import annotations

import codecs
import hashlib
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
from datetime import datetime

from PySide6.QtCore import QLockFile, QObject, QProcess, QProcessEnvironment, QTime, QTimer, Qt, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QIcon, QPainter, QPixmap
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QMenu, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton,
    QSplitter, QSystemTrayIcon, QTextEdit, QTimeEdit, QVBoxLayout, QWidget,
)

from windows_core import (
    VERSION, data_directory, is_autostart_enabled, read_json, schedule_due,
    set_autostart, validate_clients, validate_id, worker_command, write_json,
)


STYLE = """
QWidget { font-family: 'Microsoft YaHei UI', 'Segoe UI'; font-size: 13px; color: #263342; }
QMainWindow, QDialog { background: #f4f6fa; }
QFrame#sidebar { background: white; border-right: 1px solid #e5e9f0; }
QLabel#brand { font-size: 26px; font-weight: 700; color: #202b3b; }
QLabel#title { font-size: 24px; font-weight: 700; }
QLabel#muted { color: #738094; }
QLabel#status { color: #b55619; background: #fff0e3; padding: 7px 12px; border-radius: 10px; }
QPushButton { background: white; border: 1px solid #dce2eb; border-radius: 8px; padding: 9px 14px; }
QPushButton:hover { background: #edf2f9; border-color: #a8b9d0; }
QPushButton:disabled { color: #aab2bf; background: #f1f3f6; }
QPushButton#primary { background: #ed7834; color: white; border: 1px solid #ed7834; font-weight: 600; }
QPushButton#primary:hover { background: #da6725; }
QPushButton#primary:disabled { background: #efbf9f; border-color: #efbf9f; }
QPushButton#stop { color: #b93d43; }
QListWidget { background: white; border: none; outline: none; }
QListWidget::item { padding: 15px 10px; margin: 3px 0; border-radius: 8px; }
QListWidget::item:selected { background: #fff0e3; color: #b55619; }
QListWidget::item:hover { background: #f5f7fb; }
QLineEdit, QPlainTextEdit, QTextEdit, QTimeEdit { background: white; border: 1px solid #dce2eb; border-radius: 8px; padding: 8px; }
QPlainTextEdit#logs { background: #192331; color: #d7e0ec; border: none; font-family: Consolas, 'Microsoft YaHei UI'; font-size: 12px; }
QProgressBar { background: #e6eaf0; border: none; border-radius: 5px; height: 10px; text-align: center; }
QProgressBar::chunk { background: #ed7834; border-radius: 5px; }
QCheckBox { spacing: 7px; }
QSplitter::handle { background: #e5e9f0; width: 1px; }
"""


def app_icon():
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#ed7834"))
    painter.drawRoundedRect(2, 2, 60, 60, 16, 16)
    painter.setPen(QColor("white"))
    font = painter.font()
    font.setPixelSize(40)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "S")
    painter.end()
    return QIcon(pixmap)


def label(text, name=None):
    item = QLabel(text)
    if name:
        item.setObjectName(name)
    return item


def button(text, callback, name=None):
    item = QPushButton(text)
    if name:
        item.setObjectName(name)
    item.clicked.connect(callback)
    return item


class TaskController(QObject):
    log = Signal(str)
    progress = Signal(dict)
    busy_changed = Signal(bool)
    completed = Signal(str)

    def __init__(self, directory, parent=None):
        super().__init__(parent)
        self.directory = directory
        self.process = None
        self.queue = []
        self.busy = False
        self.cancelled = False
        self.failed = 0
        self.index = 0
        self.total = 0
        self.next_timer = QTimer(self)
        self.next_timer.setSingleShot(True)
        self.next_timer.timeout.connect(self._next)

    def start(self, jobs, test_mode=True, show_browser=True):
        if self.busy or not jobs:
            return False
        self.queue = list(jobs)
        self.total = len(jobs)
        self.index = self.failed = 0
        self.cancelled = False
        self.test_mode = test_mode
        self.show_browser = show_browser
        self.busy = True
        self.busy_changed.emit(True)
        self._next()
        return True

    def _next(self):
        if not self.queue or self.cancelled:
            self._finish()
            return
        mode, cid, alias = self.queue.pop(0)
        self.index += 1
        self.log.emit(f"开始：{alias}  ·  {self.index}/{self.total}")
        self.progress.emit({"percent": 0, "text": f"{alias} · 启动中"})
        process = QProcess(self)
        self.process = process
        self.decoder = codecs.getincrementaldecoder("utf-8")("replace")
        self.buffer = ""
        environment = QProcessEnvironment.systemEnvironment()
        for key, value in {
            "SPARK_DATA_DIR": str(self.directory), "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1",
            "DOUYIN_HEADLESS": "false" if self.show_browser else "true",
            "DOUYIN_TEST_MODE": "true" if self.test_mode else "false",
            "CLIENT_ALIAS": alias,
        }.items():
            environment.insert(key, value)
        process.setProcessEnvironment(environment)
        process.setWorkingDirectory(str(self.directory))
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.readyReadStandardOutput.connect(self._read)
        process.finished.connect(self._ended)
        process.errorOccurred.connect(self._error)
        command = worker_command(mode, *([cid] if cid else []))
        process.start(command[0], command[1:])

    def _read(self):
        if self.process:
            self.buffer += self.decoder.decode(bytes(self.process.readAllStandardOutput()))
            while "\n" in self.buffer:
                line, self.buffer = self.buffer.split("\n", 1)
                self._line(line.rstrip("\r"))

    def _line(self, line):
        if line.startswith("SPARK_PROGRESS:"):
            try:
                self.progress.emit(json.loads(line[len("SPARK_PROGRESS:"):]))
                return
            except (ValueError, TypeError):
                pass
        if line:
            self.log.emit(line)

    def _error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.log.emit("无法启动任务：" + self.process.errorString())
            self._ended(1, QProcess.ExitStatus.CrashExit)

    def _ended(self, code, status):
        if self.process is None:
            return
        self._read()
        self.buffer += self.decoder.decode(b"", final=True)
        if self.buffer:
            self._line(self.buffer)
        process, self.process = self.process, None
        process.deleteLater()
        if not self.cancelled:
            if code == 2:
                self.failed += 1
                self.log.emit("需要重新登录或完成验证。请选择该客户，点击「登录 / 浏览器」。")
            elif code != 0 or status == QProcess.ExitStatus.CrashExit:
                self.failed += 1
                self.log.emit(f"任务未完成（退出码 {code}），请查看上方日志。")
            else:
                self.log.emit("当前任务已结束。")
        if self.queue and not self.cancelled:
            self.log.emit("等待 5 秒后处理下一位客户…")
            self.next_timer.start(5000)
        else:
            self._finish()

    def _finish(self):
        self.busy = False
        self.busy_changed.emit(False)
        result = "任务已停止" if self.cancelled else (f"任务结束，{self.failed} 项需要处理" if self.failed else "任务已完成")
        self.completed.emit(result)

    def stop(self):
        if not self.busy:
            return
        self.cancelled = True
        self.queue.clear()
        self.next_timer.stop()
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            # Worker Job Object closes all its Chromium descendants on exit.
            self.process.kill()
        else:
            self._finish()

    def shutdown(self):
        self.stop()
        if self.process:
            self.process.waitForFinished(5000)


class ClientDialog(QDialog):
    def __init__(self, parent, cid="", client=None):
        super().__init__(parent)
        client = client or {}
        self.setWindowTitle("编辑客户" if cid else "添加客户")
        self.resize(460, 440)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.cid = QLineEdit(cid or parent.next_id())
        self.cid.setReadOnly(bool(cid))
        self.alias = QLineEdit(client.get("alias", ""))
        self.alias.setPlaceholderText("例如：张同学")
        self.friends = QPlainTextEdit("\n".join(client.get("friends", [])))
        self.friends.setPlaceholderText("每行一个好友昵称，与抖音聊天列表中的名称保持一致")
        self.active = QCheckBox("参与批量和定时任务")
        self.active.setChecked(client.get("status", "active") == "active")
        form.addRow("客户 ID", self.cid)
        form.addRow("备注名", self.alias)
        form.addRow("好友名单", self.friends)
        form.addRow("", self.active)
        layout.addLayout(form)
        hint = label("保存后，点击「登录 / 浏览器」扫码。登录完成后关闭浏览器即可保存会话。", "muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("保存")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self.validate)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def validate(self):
        try:
            validate_id(self.cid.text().strip())
            if not self.alias.text().strip():
                raise ValueError("请填写备注名。")
        except ValueError as error:
            QMessageBox.warning(self, "请检查信息", str(error))
            return
        self.accept()

    def values(self):
        cid = self.cid.text().strip()
        return cid, {"alias": self.alias.text().strip(),
                     "friends": list(dict.fromkeys(line.strip() for line in self.friends.toPlainText().splitlines() if line.strip())),
                     "status": "active" if self.active.isChecked() else "inactive"}


class SettingsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("自动化设置")
        self.resize(450, 340)
        layout = QVBoxLayout(self)
        self.autostart = QCheckBox("登录 Windows 后自动启动到托盘")
        self.autostart.setChecked(is_autostart_enabled())
        self.enabled = QCheckBox("每天定时执行所有已启用客户")
        self.enabled.setChecked(parent.settings.get("schedule_enabled", False))
        self.time = QTimeEdit(QTime.fromString(parent.settings.get("schedule_time", "09:30"), "HH:mm"))
        self.time.setDisplayFormat("HH:mm")
        self.test = QCheckBox("定时任务使用测试模式（不发送）")
        self.test.setChecked(parent.settings.get("schedule_test_mode", True))
        for item in (self.autostart, self.enabled, self.time, self.test):
            layout.addWidget(item)
        note = label("定时任务需要电脑开机且助手保持运行（可在托盘中）。\n当天错过时间会在启动或恢复后补跑一次；执行中则排到空闲后。", "muted")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch()
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("保存")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class MainWindow(QMainWindow):
    def __init__(self, directory):
        super().__init__()
        self.directory = directory
        self.clients = validate_clients(read_json(directory / "clients.json"), directory)
        self.settings = read_json(directory / "settings.json")
        self.setWindowTitle(f"火花助手 · Windows {VERSION}")
        self.setWindowIcon(app_icon())
        self.resize(1120, 760)
        self.setMinimumSize(940, 660)
        self.logger = logging.getLogger("spark.windows")
        self.logger.setLevel(logging.INFO)
        handler = RotatingFileHandler(directory / "douyin_playwright.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
        self.logger.addHandler(handler)
        self.controller = TaskController(directory, self)
        self.controller.log.connect(self.append_log)
        self.controller.progress.connect(self.update_progress)
        self.controller.busy_changed.connect(self.set_busy)
        self.controller.completed.connect(self.task_complete)
        self.build_ui()
        self.build_tray()
        self.refresh()
        self.append_log("欢迎使用火花助手 Windows 版。添加客户 → 扫码登录 → 填写好友 → 测试或执行。")
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_schedule)
        self.timer.start(15000)

    def build_ui(self):
        splitter = QSplitter()
        self.setCentralWidget(splitter)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        left = QVBoxLayout(sidebar)
        left.setContentsMargins(22, 26, 22, 22)
        left.setSpacing(14)
        left.addWidget(label("火花助手", "brand"))
        left.addWidget(label("SPARK ASSISTANT  /  WINDOWS", "muted"))
        self.count = label("客户", "muted")
        left.addWidget(self.count)
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索备注名或 ID")
        self.search.textChanged.connect(self.filter_clients)
        left.addWidget(self.search)
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self.selection_changed)
        left.addWidget(self.list, 1)
        self.add_button = button("＋ 添加客户", self.add_client, "primary")
        left.addWidget(self.add_button)
        self.import_button = button("导入客户名单", self.import_clients)
        left.addWidget(self.import_button)
        left.addWidget(button("打开数据文件夹", lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.directory)))))
        left.addWidget(label(f"版本 {VERSION}  ·  数据保存在本机", "muted"))
        splitter.addWidget(sidebar)
        content = QWidget()
        right = QVBoxLayout(content)
        right.setContentsMargins(26, 26, 26, 22)
        right.setSpacing(15)
        heading = QHBoxLayout()
        heading.addWidget(label("工作台", "title"))
        heading.addStretch()
        self.state = label("准备就绪", "status")
        heading.addWidget(self.state)
        heading.addWidget(button("设置", self.configure))
        heading.addWidget(button("退出", self.quit_app))
        right.addLayout(heading)
        self.detail = label("先添加一位客户，开始管理火花。")
        self.detail.setWordWrap(True)
        self.detail.setTextFormat(Qt.TextFormat.PlainText)
        right.addWidget(self.detail)
        row = QHBoxLayout()
        self.edit_button = button("编辑客户", self.edit_client)
        self.toggle_button = button("暂停 / 启用", self.toggle_client)
        self.delete_button = button("移除客户", self.delete_client)
        for item in (self.edit_button, self.toggle_button, self.delete_button):
            row.addWidget(item)
        row.addStretch()
        right.addLayout(row)
        actions = QHBoxLayout()
        self.run_button = button("执行当前客户", self.run_selected, "primary")
        self.batch_button = button("批量执行", self.run_all)
        self.browser_button = button("登录 / 浏览器", self.open_browser)
        self.stop_button = button("停止任务", self.controller.stop, "stop")
        self.stop_button.setEnabled(False)
        for item in (self.run_button, self.batch_button, self.browser_button, self.stop_button):
            actions.addWidget(item)
        right.addLayout(actions)
        options = QHBoxLayout()
        self.test = QCheckBox("测试模式（不发送）")
        self.test.setChecked(self.settings.get("test_mode", True))
        self.visible_browser = QCheckBox("显示浏览器")
        self.visible_browser.setChecked(self.settings.get("show_browser", True))
        options.addWidget(self.test)
        options.addWidget(self.visible_browser)
        options.addStretch()
        right.addLayout(options)
        self.progress_text = label("等待任务", "muted")
        self.progress_text.setTextFormat(Qt.TextFormat.PlainText)
        self.progress_text.setWordWrap(True)
        right.addWidget(self.progress_text)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        right.addWidget(self.progress)
        log_heading = QHBoxLayout()
        log_heading.addWidget(label("运行记录"))
        log_heading.addStretch()
        self.check_button = button("浏览器自检", self.browser_check)
        log_heading.addWidget(self.check_button)
        log_heading.addWidget(button("清空显示", lambda: self.logs.clear()))
        right.addLayout(log_heading)
        self.logs = QPlainTextEdit()
        self.logs.setObjectName("logs")
        self.logs.setReadOnly(True)
        self.logs.setMaximumBlockCount(3000)
        right.addWidget(self.logs, 1)
        self.schedule_label = label("", "muted")
        right.addWidget(self.schedule_label)
        splitter.addWidget(content)
        splitter.setSizes([290, 830])

    def build_tray(self):
        self.tray = QSystemTrayIcon(self.windowIcon(), self)
        self.tray.setToolTip("火花助手")
        menu = QMenu(self)
        menu.addAction("打开工作台", self.reveal)
        menu.addAction("停止当前任务", self.controller.stop)
        menu.addSeparator()
        menu.addAction("退出火花助手", self.quit_app)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self.reveal() if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick) else None)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

    def reveal(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def selected_id(self):
        item = self.list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def next_id(self):
        number = 1
        while f"client_{number:03d}" in self.clients:
            number += 1
        return f"client_{number:03d}"

    def refresh(self, select=None):
        cid = select or self.selected_id()
        self.list.clear()
        for key, client in self.clients.items():
            status = "已启用" if client.get("status") == "active" else "已暂停"
            item = QListWidgetItem(f"{client.get('alias', key)}\n{key}  ·  {len(client.get('friends', []))} 位好友  ·  {status}")
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.list.addItem(item)
            if cid == key:
                self.list.setCurrentItem(item)
        if self.list.currentItem() is None and self.list.count():
            self.list.setCurrentRow(0)
        active = sum(c.get("status") == "active" for c in self.clients.values())
        self.count.setText(f"客户  {len(self.clients)}  /  已启用 {active}")
        self.filter_clients()
        self.selection_changed()
        self.update_schedule_label()

    def filter_clients(self):
        query = self.search.text().casefold().strip()
        for index in range(self.list.count()):
            item = self.list.item(index)
            item.setHidden(query not in item.text().casefold())
        if self.list.currentItem() and self.list.currentItem().isHidden():
            self.list.setCurrentItem(None)
        self.selection_changed()

    def selection_changed(self, *_):
        cid = self.selected_id()
        if cid:
            client = self.clients[cid]
            friends = "、".join(client.get("friends", [])) or "尚未填写好友名单"
            self.detail.setText(f"{client.get('alias', cid)}  ·  {cid}\n{friends[:250]}")
        else:
            self.detail.setText("选择或添加一位客户。登录后填写好友名单，即可测试或执行。")
        self.set_busy(self.controller.busy)

    def set_busy(self, busy):
        selected = bool(self.selected_id())
        for item in (self.edit_button, self.toggle_button, self.delete_button, self.run_button, self.browser_button):
            item.setEnabled(selected and not busy)
        for item in (self.add_button, self.import_button, self.check_button, self.test, self.visible_browser):
            item.setEnabled(not busy)
        self.batch_button.setEnabled(not busy and any(c.get("status") == "active" for c in self.clients.values()))
        self.stop_button.setEnabled(busy)
        self.state.setText("正在运行" if busy else "准备就绪")

    def save_clients(self, clients):
        try:
            validate_clients(clients, self.directory)
            write_json(self.directory / "clients.json", clients)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "保存失败", str(error))
            return False
        self.clients = clients
        return True

    def add_client(self):
        dialog = ClientDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            cid, value = dialog.values()
            if cid in self.clients:
                QMessageBox.warning(self, "ID 已存在", "请使用另一个客户 ID，或编辑已有客户。")
                return
            value["user_data_dir"] = f"user_data_{cid}"
            if self.save_clients({**self.clients, cid: value}):
                self.refresh(cid)
                self.append_log("客户已保存。请点击「登录 / 浏览器」扫码，登录后关闭浏览器。")

    def edit_client(self):
        cid = self.selected_id()
        if not cid:
            return
        dialog = ClientDialog(self, cid, self.clients[cid])
        if dialog.exec() == QDialog.DialogCode.Accepted:
            _, value = dialog.values()
            if self.save_clients({**self.clients, cid: {**self.clients[cid], **value}}):
                self.refresh(cid)

    def toggle_client(self):
        cid = self.selected_id()
        if cid and self.save_clients({**self.clients, cid: {**self.clients[cid], "status": "inactive" if self.clients[cid].get("status") == "active" else "active"}}):
            self.refresh(cid)

    def delete_client(self):
        cid = self.selected_id()
        if not cid:
            return
        if QMessageBox.question(self, "移除客户", "移除此客户的名单记录？\n浏览器登录数据仍保留在数据文件夹中。") == QMessageBox.StandardButton.Yes:
            if self.save_clients({key: value for key, value in self.clients.items() if key != cid}):
                self.refresh()

    def import_clients(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入 clients.json（仅名单，需要重新登录）", "", "JSON (*.json)")
        if not path:
            return
        try:
            imported = read_json(Path(path))
            if set(imported) & set(self.clients):
                raise ValueError("存在重复客户 ID。为避免覆盖，请先调整导入文件中的 ID。")
            clean = {}
            for cid, value in imported.items():
                validate_id(cid)
                if not isinstance(value, dict):
                    raise ValueError("客户记录格式错误。")
                clean[cid] = {"alias": value.get("alias", cid), "friends": value.get("friends", []),
                              "status": "inactive", "user_data_dir": f"user_data_{cid}"}
            if self.save_clients({**self.clients, **clean}):
                self.refresh()
                self.append_log(f"已导入 {len(clean)} 位客户，默认暂停。请逐一重新扫码登录后启用。")
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "无法导入", str(error))

    def start_jobs(self, jobs, scheduled=False):
        if self.controller.busy:
            return False
        if not scheduled:
            self.settings.update(test_mode=self.test.isChecked(), show_browser=self.visible_browser.isChecked())
            try:
                write_json(self.directory / "settings.json", self.settings)
            except OSError as error:
                self.append_log(f"无法保存设置：{error}")
                return False
        test = self.settings.get("schedule_test_mode", True) if scheduled else self.test.isChecked()
        visible = False if scheduled else self.visible_browser.isChecked()
        return self.controller.start(jobs, test, visible)

    def run_selected(self):
        cid = self.selected_id()
        if cid:
            self.start_jobs([("run", cid, self.clients[cid].get("alias", cid))])

    def active_jobs(self):
        return [("run", cid, c.get("alias", cid)) for cid, c in self.clients.items() if c.get("status") == "active"]

    def run_all(self):
        self.start_jobs(self.active_jobs())

    def open_browser(self):
        cid = self.selected_id()
        if cid:
            self.append_log("请在浏览器中手动登录或完成验证，完成后关闭浏览器以保存登录状态。")
            self.start_jobs([("browser", cid, self.clients[cid].get("alias", cid))])

    def browser_check(self):
        self.start_jobs([("check", "", "浏览器自检")])

    def append_log(self, text):
        self.logs.appendPlainText(f"[{datetime.now():%H:%M:%S}] {text}")
        self.logger.info(text)

    def update_progress(self, value):
        self.progress.setValue(max(0, min(100, int(value.get("percent", 0)))))
        text = value.get("text", "")
        if value.get("total"):
            text += f"  ·  已处理 {value.get('processed', 0)}/{value['total']}"
        self.progress_text.setText(f"[{self.controller.index}/{self.controller.total}] {text}")

    def task_complete(self, result):
        self.append_log(result)
        self.state.setText(result)
        self.progress_text.setText(result)
        if not self.controller.failed and not self.controller.cancelled:
            self.progress.setValue(100)
        if self.tray.isVisible():
            self.tray.showMessage("火花助手", result, QSystemTrayIcon.MessageIcon.Information, 4000)

    def configure(self):
        dialog = SettingsDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        updated = {**self.settings, "schedule_enabled": dialog.enabled.isChecked(),
                   "schedule_time": dialog.time.time().toString("HH:mm"), "schedule_test_mode": dialog.test.isChecked()}
        try:
            if dialog.autostart.isChecked() != is_autostart_enabled():
                set_autostart(dialog.autostart.isChecked())
            write_json(self.directory / "settings.json", updated)
        except OSError as error:
            QMessageBox.warning(self, "设置未完整保存", str(error))
            return
        self.settings = updated
        self.update_schedule_label()
        self.append_log("自动化设置已保存。")

    def update_schedule_label(self):
        if self.settings.get("schedule_enabled"):
            mode = "测试模式" if self.settings.get("schedule_test_mode", True) else "正式执行"
            self.schedule_label.setText(f"每天 {self.settings.get('schedule_time', '09:30')}  ·  {mode}  ·  关闭窗口后继续在托盘运行")
        else:
            self.schedule_label.setText("定时任务未开启  ·  关闭窗口后可在系统托盘重新打开")

    def check_schedule(self):
        now = datetime.now()
        if self.controller.busy or not schedule_due(self.settings, now):
            return
        jobs = self.active_jobs()
        if not jobs:
            return
        updated = {**self.settings, "last_scheduled_date": now.date().isoformat()}
        try:
            # Persist before dispatch to prevent duplicate sending after a restart.
            write_json(self.directory / "settings.json", updated)
        except OSError as error:
            self.append_log(f"定时任务未启动，无法记录执行日期：{error}")
            return
        self.settings = updated
        self.append_log("开始今日定时任务。")
        self.start_jobs(jobs, scheduled=True)

    def closeEvent(self, event):
        if self.tray.isVisible():
            event.ignore()
            self.hide()
        else:
            self.controller.shutdown()
            event.accept()
            QApplication.instance().quit()

    def quit_app(self):
        if self.controller.busy:
            if QMessageBox.question(self, "退出火花助手", "退出会停止当前任务并关闭任务浏览器。确定退出？") != QMessageBox.StandardButton.Yes:
                return
        self.timer.stop()
        self.controller.shutdown()
        self.tray.hide()
        QApplication.instance().quit()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("SparkAssistant")
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    app.setQuitOnLastWindowClosed(False)
    directory = data_directory()
    name = "SparkAssistant-" + hashlib.sha256(str(directory).casefold().encode()).hexdigest()[:20]
    lock = QLockFile(str(directory / "windows-app.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(100):
        socket = QLocalSocket()
        socket.connectToServer(name)
        if socket.waitForConnected(2000):
            socket.write(b"show")
            socket.waitForBytesWritten(1000)
            socket.disconnectFromServer()
        else:
            QMessageBox.information(None, "火花助手", "助手已经在运行，请从系统托盘打开。")
        return 0
    server = QLocalServer()
    QLocalServer.removeServer(name)
    if not server.listen(name):
        QMessageBox.critical(None, "无法启动", server.errorString())
        return 1
    try:
        window = MainWindow(directory)
    except (OSError, ValueError) as error:
        QMessageBox.critical(None, "无法读取本地配置", f"{error}\n\n数据文件未改动。请检查：{directory}")
        return 1

    def activate():
        while server.hasPendingConnections():
            socket = server.nextPendingConnection()
            socket.disconnectFromServer()
            socket.deleteLater()
        window.reveal()

    server.newConnection.connect(activate)
    smoke_report = os.environ.get("SPARK_SMOKE_REPORT")
    if smoke_report:
        window.timer.stop()
        window.tray.hide()
        def finish_smoke():
            write_json(Path(smoke_report), {"status": "ok", "version": VERSION,
                                          "title": window.windowTitle(), "test_mode": window.test.isChecked()})
            app.quit()
        QTimer.singleShot(500, finish_smoke)
    if "--background" not in sys.argv or not window.tray.isVisible():
        window.show()
    app.aboutToQuit.connect(window.controller.shutdown)
    result = app.exec()
    server.close()
    lock.unlock()
    return result


if __name__ == "__main__":
    sys.exit(main())
