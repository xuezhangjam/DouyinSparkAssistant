import gi
_original_require_version = gi.require_version

def _mock_require_version(namespace, version):
    if namespace == 'AppIndicator3':
        try:
            _original_require_version('AppIndicator3', version)
            return
        except ValueError:
            _original_require_version('AyatanaAppIndicator3', version)
            import sys
            from gi.repository import AyatanaAppIndicator3
            sys.modules['gi.repository.AppIndicator3'] = AyatanaAppIndicator3
            return
    _original_require_version(namespace, version)

gi.require_version = _mock_require_version

import pystray
from PIL import Image, ImageDraw
import subprocess
import os
import psutil

def create_image():
    # 绘制一个简单的方形图标
    image = Image.new('RGB', (64, 64), color=(30, 30, 30))
    draw = ImageDraw.Draw(image)
    draw.ellipse((16, 16, 48, 48), fill=(0, 255, 0))
    return image

def on_show(icon, item):
    proj_dir = os.path.dirname(os.path.abspath(__file__))
    gui_script = os.path.join(proj_dir, "gui_gtk.py")
    # 为了保证能读取虚拟环境中的包，最好使用与托盘相同的python解释器
    import sys
    subprocess.Popen([sys.executable, gui_script])

def on_quit(icon, item):
    icon.stop()
    # 清理所有的 gui_gtk.py 进程
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['cmdline'] and 'gui_gtk.py' in ' '.join(proc.info['cmdline']):
                proc.kill()
        except:
            pass
    # 退出自己
    os._exit(0)

def main():
    icon = pystray.Icon("SparkAssistant", create_image(), "火花助手", menu=pystray.Menu(
        pystray.MenuItem('显示主界面', on_show, default=True),
        pystray.MenuItem('完全退出', on_quit)
    ))
    icon.run()

if __name__ == '__main__':
    main()
