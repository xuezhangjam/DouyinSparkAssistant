# 火花助手 (Spark Assistant)

![GTK4 UI](https://img.shields.io/badge/UI-GTK4%20%7C%20Libadwaita-blue)
![Playwright](https://img.shields.io/badge/Automation-Playwright-green)

这是一款基于 GTK4 (Libadwaita) 和 Playwright 构建的网页版自动化商业运维工具。专为具有多客户运营需求的团队设计，主要用于**全自动、防风控的批量代续火花**和自动化群发操作。

<!-- UI_SCREENSHOT_PLACEHOLDER -->
> <img width="1050" height="750" alt="image" src="https://github.com/user-attachments/assets/3ae43738-758e-4f82-b9b2-dcd132e47d77" />


## 🌟 核心特性

- **极致原生体验**：采用最现代的 GTK4 + Libadwaita 构建前端，界面丝滑优雅，并支持 Linux 原生桌面托盘管理。
- **物理级仿生防风控**：底层集成了全局指尖微调（坐标随机偏移）、移动轨迹分段阻尼等 RPA 高级特性，全面对抗 Web 前端防爬虫检测。
- **安全验证雷达**：当遭遇抖音平台验证码拦截或异地登录验证时，机器人会自动中止该客户进程、发送系统级桌面预警，并支持在控制台内【一键唤起调试浏览器】进行手工验证。
- **无人值守调度引擎**：自带开机静默自启功能，支持原生的 Cron 级别定时全自动流水线，真正的 24 小时商业级挂机。
- **上帝视角测试模式**：零风险验证新客户，开启后自动化操作将只定位并高亮目标，不会进行任何破坏性点击，并配有鼠标/键盘轨迹可视化特效。
- **(v1.3.12 新特性) 沉浸式进度显示**：独立悬浮的执行进度面板，现在完美支持显示自定义“客户备注名”，并在进度条下方实时呈现精确的“成功发送好友数”（如：[已发 2/5]），同时全局免疫 Linux 下的 `bitbrowser://` 弹窗干扰。

## 📦 安装教程

### 方式一：一键安装包（推荐）

前往 [Releases](https://github.com/xuezhangjam/DouyinSparkAssistant/releases) 下载最新版安装包，选择对应系统的格式：

| 系统 | 文件 | 安装命令 |
|---|---|---|
| Ubuntu / Debian | `.deb` | `sudo dpkg -i sparkassistant_*_amd64.deb` |
| Fedora / RHEL / CentOS | `.rpm` | `sudo rpm -i sparkassistant-*.noarch.rpm` |
| fnOS | `.fpk` | 在 fnOS 应用中心导入安装 |

> 安装完成后，在应用列表中搜索并打开 **"火花助手"** 即可。

---

### 方式二：从源码运行

#### 1. 安装系统依赖

<details>
<summary><b>Ubuntu / Debian</b></summary>

```bash
sudo apt update
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 libappindicator3-1
```
</details>

<details>
<summary><b>Fedora / RHEL / CentOS</b></summary>

```bash
sudo dnf install python3-gobject python3-cairo gtk4 libadwaita libappindicator-gtk3
```
</details>

<details>
<summary><b>Arch / Manjaro</b></summary>

```bash
sudo pacman -S python-gobject gtk4 libadwaita libappindicator-gtk3
```
</details>

<details>
<summary><b>openSUSE</b></summary>

```bash
sudo zypper install python3-gobject python3-gobject-cairo gtk4 libadwaita typelib-1_0-Gtk-4_0 typelib-1_0-Adw-1
```
</details>

#### 2. 克隆仓库、安装依赖并启动

```bash
git clone https://github.com/xuezhangjam/DouyinSparkAssistant.git
cd DouyinSparkAssistant

python3 -m venv .venv --system-site-packages
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

python tray_runner.py
```

## 🛡️ 隐私与数据安全

- **数据本地化**：本系统所有的抖音会话凭证、Cookie 数据和客户档案(`clients.json`)都会独立存储在项目运行目录下的隔离沙盒（`user_data_*`）中。
- **绝不上传**：默认配置了严格的 `.gitignore` 规则，确保您的所有私有数据绝不会被意外推送到公共代码仓库。

## ☕ 支持与赞赏 (Sponsor)

如果这个项目帮助你节省了大量的人工运营时间，或者让你学到了 GTK4 与 Playwright 的自动化架构，欢迎请作者喝杯奶茶！你的支持是我初三毕业暑假持续更新维护的最大动力！

<img src="donate.png" width="300" alt="赞赏码">

## 🤝 致谢 (Acknowledgments)

本项目的设计与核心代码逻辑由作者主导研发，并在开发过程中得到了 **Google Antigravity** 智能协作系统 (Advanced Agentic AI) 的架构辅助与极客编程支持。

## 📄 许可证 (License)

本项目采用 [MIT License](LICENSE) 开源。欢迎二次开发和提交 PR！
