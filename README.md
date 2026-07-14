# 火花助手 (Spark Assistant)

![GTK4 UI](https://img.shields.io/badge/UI-GTK4%20%7C%20Libadwaita-blue)
![Playwright](https://img.shields.io/badge/Automation-Playwright-green)

这是一款基于 GTK4 (Libadwaita) 和 Playwright 构建的网页版自动化商业运维工具。专为具有多客户运营需求的团队设计，主要用于**全自动、防风控的批量代续火花**和自动化群发操作。

<!-- UI_SCREENSHOT_PLACEHOLDER -->
> <img width="2026" height="1424" alt="image" src="https://github.com/user-attachments/assets/f5139595-d1ef-47f6-87ad-394ef93a4b96" />


## 🌟 核心特性

- **极致原生体验**：采用最现代的 GTK4 + Libadwaita 构建前端，界面丝滑优雅，并支持 Linux 原生桌面托盘管理。
- **物理级仿生防风控**：底层集成了全局指尖微调（坐标随机偏移）、移动轨迹分段阻尼等 RPA 高级特性，全面对抗 Web 前端防爬虫检测。
- **安全验证雷达**：当遭遇抖音平台验证码拦截或异地登录验证时，机器人会自动中止该客户进程、发送系统级桌面预警，并支持在控制台内【一键唤起调试浏览器】进行手工验证。
- **无人值守调度引擎**：自带开机静默自启功能，支持原生的 Cron 级别定时全自动流水线，真正的 24 小时商业级挂机。
- **上帝视角测试模式**：零风险验证新客户，开启后自动化操作将只定位并高亮目标，不会进行任何破坏性点击，并配有鼠标/键盘轨迹可视化特效。

## 📦 安装与运行

### 1. 安装系统依赖 (以 Ubuntu/Debian 为例)
本项目使用了原生的 GTK4 和 Libadwaita 绑定，需要先在系统层面安装依赖：
```bash
sudo apt update
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 libappindicator3-1
```

### 2. 配置 Python 虚拟环境
为了能够访问系统级的 GTK 库，创建虚拟环境时必须带上 `--system-site-packages` 参数：
```bash
python3 -m venv .venv --system-site-packages
source .venv/bin/activate
```

### 3. 安装项目依赖
```bash
pip install -r requirements.txt
playwright install chromium
```

### 4. 启动控制台
```bash
python tray_runner.py
# 或直接启动图形界面：
# python gui_gtk.py
```

## 🛡️ 隐私与数据安全

- **数据本地化**：本系统所有的抖音会话凭证、Cookie 数据和客户档案(`clients.json`)都会独立存储在项目运行目录下的隔离沙盒（`user_data_*`）中。
- **绝不上传**：默认配置了严格的 `.gitignore` 规则，确保您的所有私有数据绝不会被意外推送到公共代码仓库。

## 📄 许可证 (License)

本项目采用 [MIT License](LICENSE) 开源。欢迎二次开发和提交 PR！
