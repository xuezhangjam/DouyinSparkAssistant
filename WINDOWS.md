# 火花助手 Windows 版

版本：1.4.0-win.1。适用于 Windows 10 / 11 x64；当前开发机完成 Windows 实测，其他机器仍需验证。

## 直接运行

1. 将 `SparkAssistant-1.4.0-win.1-Windows-x64.zip` 完整解压到固定文件夹。
2. 双击 `SparkAssistant.exe`。无需另外安装 Python、GTK、WSL 或浏览器。
3. 添加客户，填写备注和好友名单（每行一个，与聊天列表昵称一致）。
4. 选择客户，点击「登录 / 浏览器」，在抖音网页中手动扫码。完成后关闭浏览器，保存登录状态。
5. 默认勾选「测试模式（不发送）」。确认定位正确后，取消此选项再执行当前客户或批量任务。

保留 `SparkWorker.exe` 和 `_internal` 文件夹，不要只复制主程序。运行时需要网络访问抖音。
这是未签名的便携测试版，没有安装器或自动更新器；请核对来源与同目录 SHA256 校验文件。

## 功能

- 原生 Qt 桌面界面，中文客户搜索、添加、编辑、暂停/启用与名单导入。
- 每位客户独立浏览器登录目录，单客户与顺序批量执行，实时日志与进度。
- 测试模式与可见/后台浏览器；需登录或验证时提示用户手动处理。
- 关闭窗口后留在系统托盘；从托盘或再次双击主程序打开同一个窗口。
- 停止任务、程序退出或任务进程异常退出时，清理该任务的浏览器子进程。
- 可选 Windows 登录自启与每日定时任务，均默认关闭。

定时任务需要电脑处于开机状态，且助手正在运行（可以隐藏在托盘）。不唤醒睡眠中的电脑。
每天到点执行一次；当天错过时间，会在启动/恢复后补跑一次，忙碌时等当前任务结束。
每日执行标记在开始前保存：失败或中途停止当天不会自动重试，可手动执行，避免重复发送。
定时任务有独立的测试模式选项，默认不发送。退出助手后不再触发任务。
开机自启仅修改当前用户的 `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\DouyinSparkAssistant`。
移动程序文件夹后，应在设置中关闭并重新开启自启，更新路径。

## 数据和迁移

数据保存在 `%LOCALAPPDATA%\SparkAssistant`，在界面点击「打开数据文件夹」即可找到：

- `clients.json`：客户名单，与原项目字段兼容。
- `user_data_<客户ID>`：浏览器会话，包含敏感登录信息，切勿公开分享。
- `settings.json`：本机设置和当天定时执行标记。
- `douyin_playwright.log`：日志，每份最多约 5 MB，保留 3 份轮转备份。

升级时替换程序文件夹即可保留数据。打包脚本只包含程序和浏览器，不包含客户资料。
导入旧版 `clients.json` 只迁移名单，新导入客户默认暂停；跨系统请重新扫码登录。
移除客户仅移除名单，保留浏览器会话目录。程序不会自动删除个人资料。
高级用途可用 `SPARK_DATA_DIR` 环境变量指定独立数据目录。

## 从源码运行 / 重新打包

使用 Windows x64 Python 3.11–3.13（本次验证为 3.13），在项目目录运行：

```powershell
py -3 -m venv .venv-win
.\.venv-win\Scripts\python.exe -m pip install -r requirements-windows.txt
$env:PLAYWRIGHT_BROWSERS_PATH = "$PWD\.windows-browsers"
.\.venv-win\Scripts\python.exe -m playwright install chromium
.\.venv-win\Scripts\python.exe windows_app.py
```

安装好依赖后也可双击 `start_windows.bat`。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\build_windows.ps1
```

脚本创建项目内虚拟环境，安装锁定版本依赖，下载 Chromium，运行测试，构建两个程序，执行打包后的浏览器自检，并生成 ZIP 和 SHA256。不会更改系统执行策略。
产物在 `dist`，GitHub Actions 的 Windows 构建工作流也可生成相同产物。

## 验证范围和边界

Windows 移植复用根目录 `runner.py` 的抖音自动化逻辑；本地自检使用离线测试页面，不会自动登录或发消息。
真实扫码、好友匹配和发送仍需用你自己的账号验收。抖音页面改变、验证码和登录失效都可能影响执行。
进度中的「已处理」表示已遍历的目标数，不表示服务端确认送达；退出码成功也不能证明消息送达。
Windows 入口提供桌面控制台，不启动旧版 Web 管理服务。原 Linux / NAS 入口保持独立。

## 第三方组件

Qt / PySide6 以动态库方式随程序分发，适用 LGPLv3 / GPL 或商业许可；相关许可位于 `_internal` 的包元数据目录。
PySide6 源码与许可见 <https://code.qt.io/cgit/pyside/pyside-setup.git/>，Qt 源码见 <https://code.qt.io/>。
Playwright 使用 Apache 2.0，Chromium 的第三方许可随浏览器目录分发。
构建方式参考 [Playwright 打包文档](https://playwright.dev/python/docs/library#pyinstaller) 与 [Qt 打包文档](https://doc.qt.io/qtforpython-6/deployment/deployment-pyinstaller.html)。
