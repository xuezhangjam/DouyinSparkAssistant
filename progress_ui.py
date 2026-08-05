import sys
import threading
import os
import gi

# 强制使用 X11 后端，以便在 Wayland 下通过 XWayland 获得绝对定位能力
os.environ["GDK_BACKEND"] = "x11"

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

class ProgressWindow(Gtk.Window):
    def __init__(self):
        # 使用 POPUP 类型可以脱离窗口管理器的各种限制，甚至置顶
        super().__init__(type=Gtk.WindowType.POPUP)
        self.set_title("任务进度")
        
        # 极简尺寸
        self.set_default_size(300, 48)
        self.set_resizable(False)
        self.set_keep_above(True) # 强制置顶
        
        # 居中偏下显示 (屏幕底部上方 100px)
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor()
        if monitor:
            geometry = monitor.get_geometry()
            x = geometry.x + (geometry.width - 300) // 2
            y = geometry.y + geometry.height - 120
            self.move(x, y)

        # 黑色/深灰背景，圆角样式 (简单的CSS)
        css = b"""
        window {
            background-color: #2b2b2b;
            border: 1px solid #444;
            border-radius: 8px;
        }
        label { color: #fff; }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), 
            provider, 
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        main_box.set_margin_top(8)
        main_box.set_margin_bottom(8)
        main_box.set_margin_start(12)
        main_box.set_margin_end(12)
        self.add(main_box)
        
        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        main_box.pack_start(left_box, True, True, 0)
        
        self.lbl_title = Gtk.Label(label="正在准备任务...")
        self.lbl_title.set_xalign(0.0)
        left_box.pack_start(self.lbl_title, False, False, 0)
        
        self.progress = Gtk.ProgressBar()
        self.progress.set_fraction(0.0)
        left_box.pack_start(self.progress, False, False, 0)
        
        self.lbl_sub = Gtk.Label(label="请稍候...")
        self.lbl_sub.set_xalign(0.0)
        self.lbl_sub.set_markup("<small>请稍候...</small>")
        left_box.pack_start(self.lbl_sub, False, False, 0)
        
        btn_cancel = Gtk.Button()
        # 内部放一个红色的 X
        lbl_x = Gtk.Label(label="<span color='#ff5555' weight='bold'>✖</span>")
        lbl_x.set_use_markup(True)
        btn_cancel.add(lbl_x)
        btn_cancel.set_relief(Gtk.ReliefStyle.NONE)
        btn_cancel.set_valign(Gtk.Align.CENTER)
        btn_cancel.connect("clicked", self.on_cancel)
        main_box.pack_end(btn_cancel, False, False, 0)
        
        # 使窗口可拖动
        self.connect("button-press-event", self.on_button_press)

        threading.Thread(target=self.read_stdin, daemon=True).start()

    def on_button_press(self, widget, event):
        if event.button == 1: # 左键
            self.begin_move_drag(event.button, event.x_root, event.y_root, event.time)
            return True

    def on_cancel(self, btn):
        sys.exit(1)

    def update_ui(self, percent, text):
        if percent is not None:
            self.progress.set_fraction(percent / 100.0)
        if text is not None:
            self.lbl_title.set_text(text)
            self.lbl_sub.set_markup(f"<small>已完成 {int(percent or self.progress.get_fraction()*100)}%</small>")

    def read_stdin(self):
        for line in iter(sys.stdin.readline, ''):
            line = line.strip()
            if not line:
                continue
            
            percent = None
            text = None
            
            if line.startswith('#'):
                text = line[1:].strip()
            else:
                try:
                    percent = float(line)
                    if percent >= 100:
                        GLib.idle_add(lambda: sys.exit(0))
                        return
                except:
                    pass
            
            GLib.idle_add(self.update_ui, percent, text)

if __name__ == "__main__":
    win = ProgressWindow()
    win.show_all()
    Gtk.main()
