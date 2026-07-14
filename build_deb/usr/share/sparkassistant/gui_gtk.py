import sys
import os
import json
import subprocess
import threading
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Pango, Gio

CONFIG_FILE = "clients.json"
RUNNER_SCRIPT = "runner.py"
SCHEDULER_SCRIPT = "scheduler.py"

class ClientDialog(Gtk.Window):
    def __init__(self, parent, is_edit=False, client_id="", alias="", friends=None):
        super().__init__(title="修改客户信息" if is_edit else "录入新客户", transient_for=parent, modal=True)
        self.set_default_size(400, 500)
        self.parent_win = parent
        self.is_edit = is_edit
        self.client_id = client_id
        
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        main_box.set_margin_top(12)
        main_box.set_margin_bottom(12)
        main_box.set_margin_start(12)
        main_box.set_margin_end(12)
        
        # 客户ID
        id_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        id_box.append(Gtk.Label(label="客户ID:"))
        self.entry_id = Gtk.Entry(hexpand=True)
        if is_edit or client_id:
            self.entry_id.set_text(client_id)
            self.entry_id.set_sensitive(False)
        id_box.append(self.entry_id)
        main_box.append(id_box)
        
        # 备注名
        alias_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        alias_box.append(Gtk.Label(label="备注名:"))
        self.entry_alias = Gtk.Entry(hexpand=True)
        self.entry_alias.set_text(alias)
        alias_box.append(self.entry_alias)
        main_box.append(alias_box)
        
        # 好友列表
        main_box.append(Gtk.Label(label="好友名单:", xalign=0))
        
        scrolled = Gtk.ScrolledWindow(vexpand=True)
        self.friends_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        scrolled.set_child(self.friends_box)
        main_box.append(scrolled)
        
        self.friend_entries = []
        if friends:
            for f in friends:
                self.add_friend_row(f)
        else:
            self.add_friend_row("")
            
        btn_add_friend = Gtk.Button(label="➕ 添加一个好友")
        btn_add_friend.connect("clicked", lambda x: self.add_friend_row(""))
        main_box.append(btn_add_friend)
        
        # 底部按钮
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, halign=Gtk.Align.END)
        btn_cancel = Gtk.Button(label="取消")
        btn_cancel.connect("clicked", lambda x: self.destroy())
        btn_save = Gtk.Button(label="保存")
        btn_save.add_css_class("suggested-action")
        btn_save.connect("clicked", self.on_save)
        btn_box.append(btn_cancel)
        btn_box.append(btn_save)
        
        main_box.append(btn_box)
        self.set_child(main_box)
        
    def add_friend_row(self, text):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        entry = Gtk.Entry(hexpand=True)
        entry.set_text(text)
        entry.set_placeholder_text("输入好友名字")
        self.friend_entries.append(entry)
        
        btn_del = Gtk.Button(label="❌")
        btn_del.connect("clicked", self.on_del_friend_row, row, entry)
        
        row.append(entry)
        row.append(btn_del)
        self.friends_box.append(row)
        
    def on_del_friend_row(self, btn, row, entry):
        if entry in self.friend_entries:
            self.friend_entries.remove(entry)
        self.friends_box.remove(row)
        
    def on_save(self, btn):
        cid = self.entry_id.get_text().strip()
        alias = self.entry_alias.get_text().strip()
        if not cid or not alias:
            self.parent_win.append_log("⚠️ 错误：客户ID和备注名为必填项！")
            return
            
        friends = [e.get_text().strip() for e in self.friend_entries if e.get_text().strip()]
        
        config = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                try:
                    config = json.load(f)
                except:
                    pass
                    
        if self.is_edit:
            if cid in config:
                config[cid]["alias"] = alias
                config[cid]["friends"] = friends
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=4, ensure_ascii=False)
                self.parent_win.append_log(f"✅ 客户【{alias}】信息修改成功！")
                self.parent_win.load_clients()
                self.destroy()
        else:
            friends_str = ",".join(friends)
            self.parent_win.append_log(f"准备录入新客户: {alias}")
            self.parent_win.run_script("add_client_gui.py", [cid, alias, friends_str])
            self.destroy()

class SettingsDialog(Adw.Window):
    def __init__(self, parent):
        super().__init__(title="自动化配置", transient_for=parent, modal=True)
        self.set_default_size(400, 300)
        self.parent_win = parent
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        header = Gtk.HeaderBar()
        box.append(header)
        
        btn_save = Gtk.Button(label="保存并应用")
        btn_save.add_css_class("suggested-action")
        btn_save.connect("clicked", self.on_save)
        header.pack_end(btn_save)
        
        page = Adw.PreferencesPage()
        group = Adw.PreferencesGroup(title="系统级无人值守")
        page.add(group)
        
        # 开机自启
        self.row_autostart = Adw.SwitchRow(title="开机后台自启", subtitle="电脑开机时自动静默挂机，不弹界面")
        self.row_autostart.set_active(self.check_autostart())
        group.add(self.row_autostart)
        
        # 定时执行
        cron_status, cron_time = self.check_cron()
        self.row_cron = Adw.SwitchRow(title="定时全自动流水线", subtitle="每天定时触发【批量全自动】任务")
        self.row_cron.set_active(cron_status)
        group.add(self.row_cron)
        
        # 炫酷时间选择器
        self.time_row = Adw.ActionRow(title="触发时间 (24小时制)")
        self.time_row.set_visible(cron_status)
        
        time_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, valign=Gtk.Align.CENTER)
        time_box.set_margin_top(6)
        time_box.set_margin_bottom(6)
        
        # 解析已有的 cron_time (例如 "09:30")
        try:
            h_str, m_str = cron_time.split(":")
            h, m = int(h_str), int(m_str)
        except:
            h, m = 9, 30
            
        def format_spin(spin):
            val = spin.get_adjustment().get_value()
            spin.set_text(f"{int(val):02d}")
            return True
            
        # 小时拨轮
        adj_h = Gtk.Adjustment(value=h, lower=0, upper=23, step_increment=1)
        self.spin_h = Gtk.SpinButton(adjustment=adj_h, orientation=Gtk.Orientation.VERTICAL, numeric=True, width_chars=2)
        self.spin_h.add_css_class("title-1")
        self.spin_h.connect("output", format_spin)
        
        # 冒号分隔符
        lbl_colon = Gtk.Label(label=":")
        lbl_colon.add_css_class("title-1")
        
        # 分钟拨轮
        adj_m = Gtk.Adjustment(value=m, lower=0, upper=59, step_increment=1)
        self.spin_m = Gtk.SpinButton(adjustment=adj_m, orientation=Gtk.Orientation.VERTICAL, numeric=True, width_chars=2)
        self.spin_m.add_css_class("title-1")
        self.spin_m.connect("output", format_spin)
        
        time_box.append(self.spin_h)
        time_box.append(lbl_colon)
        time_box.append(self.spin_m)
        
        self.time_row.add_suffix(time_box)
        
        # 当开关变化时，显示/隐藏时间拨轮
        self.row_cron.connect("notify::active", lambda *args: self.time_row.set_visible(self.row_cron.get_active()))
        group.add(self.time_row)
        
        box.append(page)
        self.set_content(box)
        
    def check_autostart(self):
        autostart_path = os.path.expanduser("~/.config/autostart/douyin_auto.desktop")
        return os.path.exists(autostart_path)
        
    def check_cron(self):
        try:
            output = subprocess.check_output(["crontab", "-l"], text=True, stderr=subprocess.DEVNULL)
            for line in output.split('\n'):
                if "scheduler.py" in line and not line.strip().startswith('#'):
                    # Parse cron time, e.g. "30 9 * * * ..." -> 09:30
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        minute, hour = parts[0], parts[1]
                        return True, f"{int(hour):02d}:{int(minute):02d}"
        except:
            pass
        return False, "09:30"
        
    def on_save(self, btn):
        # 处理开机自启
        autostart_dir = os.path.expanduser("~/.config/autostart")
        autostart_path = os.path.join(autostart_dir, "douyin_auto.desktop")
        
        
        proj_dir = os.path.dirname(os.path.abspath(__file__))
        if self.row_autostart.get_active():
            os.makedirs(autostart_dir, exist_ok=True)
            runner_cmd = f"bash -c 'cd {proj_dir} && source .venv/bin/activate && DOUYIN_HEADLESS=true python scheduler.py'"
            desktop_content = f"[Desktop Entry]\nType=Application\nName=Spark Assistant\nExec={runner_cmd}\nHidden=false\nNoDisplay=false\nX-GNOME-Autostart-enabled=true\n"
            with open(autostart_path, 'w') as f:
                f.write(desktop_content)
            self.parent_win.append_log("✅ 开机后台自启已开启！")
        else:
            if os.path.exists(autostart_path):
                os.remove(autostart_path)
            self.parent_win.append_log("ℹ️ 开机后台自启已关闭。")
            
        # 处理定时任务
        hour = int(self.spin_h.get_value())
        minute = int(self.spin_m.get_value())
        time_str = f"{hour:02d}:{minute:02d}"
        
        try:
            old_crontab = subprocess.check_output(["crontab", "-l"], text=True, stderr=subprocess.DEVNULL)
        except:
            old_crontab = ""
            
        new_lines = [line for line in old_crontab.split('\n') if "scheduler.py" not in line and line.strip()]
        
        if self.row_cron.get_active():
            proj_dir = os.path.dirname(os.path.abspath(__file__))
            cron_cmd = f"{int(minute)} {int(hour)} * * * cd {proj_dir} && source .venv/bin/activate && DOUYIN_HEADLESS=true {proj_dir}/.venv/bin/python scheduler.py > /tmp/douyin_cron.log 2>&1"
            new_lines.append(cron_cmd)
            self.parent_win.append_log(f"✅ 定时全自动任务已设定为每天 {time_str} 执行！")
        else:
            self.parent_win.append_log("ℹ️ 定时任务已关闭。")
            
        new_crontab = "\n".join(new_lines) + "\n"
        
        proc = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE, text=True)
        proc.communicate(new_crontab)
        
        self.destroy()

class DouyinApp(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="火花助手 (GTK4)")
        self.set_default_size(1000, 700)
        
        self.process = None
        self.selected_cid = None
        
        # 主分割面板
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_position(300)
        self.set_content(paned)
        
        self.connect("close-request", self.on_close_request)
        
        # --- 左侧布局 ---
        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        left_box.set_size_request(250, -1)
        
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)
        left_box.append(header)
        
        title_label = Gtk.Label(label="<b>客户列表</b>", use_markup=True)
        title_label.set_margin_top(6)
        title_label.set_margin_bottom(6)
        left_box.append(title_label)
        
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.connect("row-selected", self.on_row_selected)
        self.listbox.add_css_class("boxed-list")
        self.listbox.set_margin_start(12)
        self.listbox.set_margin_end(12)
        
        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_child(self.listbox)
        left_box.append(scroll)
        
        btn_add = Gtk.Button(label="➕ 扫码录入新客户")
        btn_add.set_margin_top(12)
        btn_add.set_margin_bottom(12)
        btn_add.set_margin_start(12)
        btn_add.set_margin_end(12)
        btn_add.add_css_class("suggested-action")
        btn_add.connect("clicked", self.on_add_client)
        left_box.append(btn_add)
        
        paned.set_start_child(left_box)
        
        # --- 右侧布局 ---
        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        right_box.set_size_request(450, -1)
        right_header = Adw.HeaderBar()
        right_header.set_show_title(False)
        
        btn_settings = Gtk.Button(icon_name="emblem-system-symbolic")
        btn_settings.add_css_class("flat")
        btn_settings.set_tooltip_text("自动化设置")
        btn_settings.connect("clicked", self.on_settings)
        right_header.pack_end(btn_settings)
        
        btn_sponsor = Gtk.Button(icon_name="starred-symbolic")
        btn_sponsor.add_css_class("flat")
        btn_sponsor.set_tooltip_text("支持与赞赏")
        btn_sponsor.connect("clicked", self.on_sponsor)
        right_header.pack_end(btn_sponsor)
        
        right_box.append(right_header)
        
        # 操作按钮区
        control_box = Gtk.FlowBox()
        control_box.set_selection_mode(Gtk.SelectionMode.NONE)
        control_box.set_max_children_per_line(10)
        control_box.set_column_spacing(6)
        control_box.set_row_spacing(6)
        control_box.set_margin_top(6)
        control_box.set_margin_bottom(6)
        control_box.set_margin_start(6)
        control_box.set_margin_end(6)
        
        btn_single = Gtk.Button(label="▶ 单独续火花")
        btn_single.add_css_class("pill")
        btn_single.connect("clicked", self.on_run_single)
        control_box.append(btn_single)
        
        btn_all = Gtk.Button(label="🔥 批量全自动")
        btn_all.add_css_class("pill")
        btn_all.add_css_class("destructive-action")
        btn_all.connect("clicked", self.on_run_all)
        control_box.append(btn_all)
        
        btn_browser = Gtk.Button(label="🌐 调试浏览器")
        btn_browser.add_css_class("pill")
        btn_browser.connect("clicked", self.on_run_browser)
        control_box.append(btn_browser)
        
        btn_stop = Gtk.Button(label="🛑 停止任务")
        btn_stop.add_css_class("pill")
        btn_stop.connect("clicked", self.on_stop)
        control_box.append(btn_stop)
        
        btn_clear = Gtk.Button(label="🗑️ 清空日志")
        btn_clear.add_css_class("pill")
        btn_clear.connect("clicked", self.on_clear_log)
        control_box.append(btn_clear)
        
        self.chk_browser = Gtk.CheckButton(label="显示浏览器(测试)")
        self.chk_browser.set_active(True)
        control_box.append(self.chk_browser)
        
        self.chk_test = Gtk.CheckButton(label="🧪 测试模式(只定位不发送)")
        control_box.append(self.chk_test)
        
        right_box.append(control_box)
        
        # 日志区
        self.textview = Gtk.TextView(vexpand=True, editable=False)
        # 黑色背景，绿色字体
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"textview { background-color: #1e1e1e; color: #00ff00; font-family: monospace; font-size: 13px; }")
        self.textview.get_style_context().add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        
        self.textbuffer = self.textview.get_buffer()
        log_scroll = Gtk.ScrolledWindow(vexpand=True)
        log_scroll.set_child(self.textview)
        right_box.append(log_scroll)
        
        paned.set_end_child(right_box)
        
        self.load_clients()
        
    def get_next_client_id(self):
        if not os.path.exists(CONFIG_FILE): return "client_001"
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except: return "client_001"
        
        max_num = 0
        for cid in config.keys():
            if cid.startswith("client_"):
                try:
                    num = int(cid.split("_")[1])
                    if num > max_num: max_num = num
                except: pass
        return f"client_{max_num + 1:03d}"

    def load_clients(self):
        # 清空
        while child := self.listbox.get_first_child():
            self.listbox.remove(child)
            
        if not os.path.exists(CONFIG_FILE): return
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except: return
        
        for cid, data in self.config.items():
            alias = data.get("alias", cid)
            row = Gtk.ListBoxRow()
            row.cid = cid # 保存引用
            
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            box.set_margin_top(6)
            box.set_margin_bottom(6)
            box.set_margin_start(6)
            box.set_margin_end(6)
            
            lbl = Gtk.Label(label=f"<b>{alias}</b>\n<small>{cid}</small>", use_markup=True, hexpand=True, xalign=0)
            box.append(lbl)
            
            # 状态切换开关
            switch_status = Gtk.Switch(valign=Gtk.Align.CENTER)
            switch_status.set_active(data.get("status", "active") == "active")
            switch_status.connect("notify::active", self.on_client_status_changed, cid)
            switch_status.set_tooltip_text("开启或跳过该客户")
            box.append(switch_status)
            
            btn_edit = Gtk.Button(icon_name="document-edit-symbolic")
            btn_edit.add_css_class("flat")
            btn_edit.connect("clicked", self.on_edit_client, cid)
            box.append(btn_edit)
            
            btn_del = Gtk.Button(icon_name="user-trash-symbolic")
            btn_del.add_css_class("flat")
            btn_del.add_css_class("error")
            btn_del.connect("clicked", self.on_del_client, cid)
            box.append(btn_del)
            
            row.set_child(box)
            self.listbox.append(row)

    def on_row_selected(self, listbox, row):
        if row:
            self.selected_cid = row.cid

    def on_client_status_changed(self, switch, gparam, cid):
        if cid in self.config:
            new_status = "active" if switch.get_active() else "inactive"
            self.config[cid]["status"] = new_status
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            status_text = "🟢 已启用" if switch.get_active() else "⚪ 已暂停"
            self.append_log(f"更新状态: 客户 {cid} {status_text}")

    def on_close_request(self, win):
        self.set_visible(False)
        self.append_log("ℹ️ 窗口已最小化到托盘运行。")
        return True # 取消默认关闭行为

    def append_log(self, text):
        def _append():
            end_iter = self.textbuffer.get_end_iter()
            self.textbuffer.insert(end_iter, text + "\n")
            # 自动滚动
            mark = self.textbuffer.create_mark(None, self.textbuffer.get_end_iter(), False)
            self.textview.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)
        GLib.idle_add(_append)

    # --- 按钮事件 ---
    def on_settings(self, btn):
        dialog = SettingsDialog(self)
        dialog.present()

    def on_add_client(self, btn):
        dialog = ClientDialog(self, is_edit=False, client_id=self.get_next_client_id())
        dialog.present()

    def on_edit_client(self, btn, cid):
        if cid not in self.config: return
        c = self.config[cid]
        dialog = ClientDialog(self, is_edit=True, client_id=cid, alias=c.get("alias",""), friends=c.get("friends",[]))
        dialog.present()

    def on_del_client(self, btn, cid):
        if cid not in self.config: return
        
        dialog = Adw.MessageDialog(
            heading="确认删除客户？",
            body=f"您确定要彻底删除客户【{self.config[cid].get('alias', cid)}】吗？\n此操作不可撤销，且会清除关联的浏览器登录数据。",
            transient_for=self
        )
        dialog.add_response("cancel", "取消")
        dialog.add_response("delete", "删除")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        
        def on_response(dlg, response):
            if response == "delete":
                import shutil
                c = self.config[cid]
                user_data_dir = c.get("user_data_dir", f"user_data_{cid}")
                full_dir = os.path.join(os.getcwd(), user_data_dir)
                del self.config[cid]
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(self.config, f, indent=4, ensure_ascii=False)
                if os.path.exists(full_dir):
                    shutil.rmtree(full_dir, ignore_errors=True)
                self.append_log(f"🗑️ 客户 {cid} 已被彻底删除！")
                self.load_clients()
                
        dialog.connect("response", on_response)
        dialog.present()

    def on_run_single(self, btn):
        if not self.selected_cid:
            self.append_log("⚠️ 请先在左侧选择一个客户！")
            return
        self.append_log(f"准备单独运行客户: {self.selected_cid}")
        self.run_script(RUNNER_SCRIPT, [self.selected_cid], not self.chk_browser.get_active())

    def on_run_all(self, btn):
        self.append_log("准备执行批量任务调度...")
        self.run_script(SCHEDULER_SCRIPT, [], not self.chk_browser.get_active())

    def on_run_browser(self, btn):
        if not self.selected_cid:
            self.append_log("⚠️ 请先在左侧选择一个客户！")
            return
        self.append_log(f"准备调试浏览器: {self.selected_cid}")
        self.run_script("open_browser.py", [self.selected_cid], headless=False)

    def on_stop(self, btn):
        if self.process:
            self.process.terminate()
            self.append_log("\n🛑 已发送终止信号！")

    def on_clear_log(self, btn):
        self.textbuffer.set_text("")

    def run_script(self, script_name, args, headless=True):
        if self.process and self.process.poll() is None:
            self.append_log("⚠️ 当前有任务正在运行，请先停止！")
            return
            
        self.textbuffer.set_text("") # 清空日志
        cmd = [os.path.join(os.getcwd(), ".venv", "bin", "python"), script_name] + args
        self.append_log(f"🚀 开始执行: {' '.join(cmd)}\n" + "="*50)
        
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["DOUYIN_HEADLESS"] = "true" if headless else "false"
        env["DOUYIN_TEST_MODE"] = "true" if self.chk_test.get_active() else "false"
        
        self.process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env, bufsize=1
        )
        
        # 启动读线程
        threading.Thread(target=self._read_output, args=(self.process,), daemon=True).start()
        
    def _read_output(self, proc):
        for line in iter(proc.stdout.readline, ''):
            self.append_log(line.strip('\n'))
        proc.stdout.close()
        proc.wait()
        self.append_log("="*50 + f"\n✅ 任务结束，退出码: {proc.returncode}")
        GLib.idle_add(self.load_clients) # 刷新列表
        
        # 发送系统通知
        def _notify():
            notification = Gio.Notification.new("代挂任务已完成")
            notification.set_body("所有后台续火花任务执行完毕。")
            notification.set_default_action("app.activate")
            try:
                self.get_application().send_notification("task-complete", notification)
            except:
                pass
        GLib.idle_add(_notify)

class MyApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.douyin.commercial")
        self.connect("activate", self.on_activate)
        self.tray_process = None
        
        # 定义唤醒动作
        action = Gio.SimpleAction.new("activate", None)
        action.connect("activate", lambda a, v: self.on_activate(self))
        self.add_action(action)
        
    def on_activate(self, app):
        windows = self.get_windows()
        if windows:
            win = windows[0]
        else:
            win = DouyinApp(self)
            # 尝试启动托盘
            if self.tray_process is None or self.tray_process.poll() is not None:
                self.tray_process = subprocess.Popen(
                    [os.path.join(os.getcwd(), ".venv", "bin", "python"), "tray_runner.py"],
                    cwd=os.path.join(os.getcwd())
                )
        win.present()

if __name__ == "__main__":
    app = MyApp()
    sys.exit(app.run(sys.argv))
