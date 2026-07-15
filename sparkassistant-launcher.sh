#!/bin/bash
# Spark Assistant Smart Launcher
# 这段脚本负责在用户首次启动时，智能初始化虚拟环境并下载依赖。

APP_DIR="/usr/share/sparkassistant"
USER_DATA_DIR="$HOME/.local/share/SparkAssistant"
VENV_DIR="$USER_DATA_DIR/venv"

echo "启动火花助手..."

# 确保用户数据目录存在
mkdir -p "$USER_DATA_DIR"

# 检查虚拟环境是否已经建立
if [ ! -d "$VENV_DIR" ]; then
    echo "========================================="
    echo "首次启动初始化中，请保持网络通畅..."
    echo "========================================="
    
    # 创建带系统依赖的虚拟环境 (为了支持 GTK4)
    python3 -m venv "$VENV_DIR" --system-site-packages
    
    # 激活环境并安装要求
    source "$VENV_DIR/bin/activate"
    pip install -r "$APP_DIR/requirements.txt"
    
    # 智能下载 Playwright 浏览器依赖
    echo "正在下载运行所需的自动化浏览器内核..."
    playwright install chromium
    
    echo "========================================="
    echo "初始化完成！即将为您打开控制台..."
    echo "========================================="
else
    source "$VENV_DIR/bin/activate"
    # 检查是否有新增依赖（用于旧版本升级时的自动修复）
    if ! python3 -c "import pystray, fastapi, uvicorn" 2>/dev/null; then
        echo "检测到新版本依赖，正在为您自动升级..."
        pip install -r "$APP_DIR/requirements.txt"
    fi
fi

# 切换到用户数据目录以保证读写权限
cd "$USER_DATA_DIR" || exit 1

# 启动主程序
python3 "$APP_DIR/tray_runner.py"
