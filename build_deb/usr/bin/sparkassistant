#!/bin/bash
# Spark Assistant Smart Launcher
# 这段脚本负责在用户首次启动时，智能初始化虚拟环境并下载依赖。

APP_DIR="/usr/share/sparkassistant"
USER_DATA_DIR="$HOME/.local/share/SparkAssistant"
VENV_DIR="$USER_DATA_DIR/venv"
LOCK_FILE="$USER_DATA_DIR/.launcher.lock"

echo "启动火花助手..."

# 确保用户数据目录存在
mkdir -p "$USER_DATA_DIR"

# 检查是否有其它实例正在执行初始化
exec 200>"$LOCK_FILE"
if ! flock -n 200; then
    if command -v zenity >/dev/null 2>&1; then
        zenity --info --text="火花助手正在后台进行初始化或环境升级，请耐心等待几分钟..." --title="火花助手提示" --timeout=3
    fi
    exit 1
fi

# 检查虚拟环境是否已经建立
if [ ! -d "$VENV_DIR" ]; then
    echo "========================================="
    echo "首次启动初始化中，请保持网络通畅..."
    echo "========================================="
    
    if command -v zenity >/dev/null 2>&1; then
        (
            echo "10"; echo "# 创建虚拟环境..."
            python3 -m venv "$VENV_DIR" --system-site-packages
            echo "30"; echo "# 正在安装基础依赖..."
            source "$VENV_DIR/bin/activate"
            pip install -r "$APP_DIR/requirements.txt"
            echo "60"; echo "# 正在下载自动化浏览器内核 (文件较大，请耐心等待)..."
            playwright install chromium
            echo "100"; echo "# 初始化完成！"
        ) | zenity --progress --title="火花助手首次配置" --text="准备初始化..." --percentage=0 --auto-close --auto-kill
    else
        python3 -m venv "$VENV_DIR" --system-site-packages
        source "$VENV_DIR/bin/activate"
        pip install -r "$APP_DIR/requirements.txt"
        playwright install chromium
    fi
else
    source "$VENV_DIR/bin/activate"
    # 检查是否有新增依赖（用于旧版本升级时的自动修复）
    if ! python3 -c "import pystray, fastapi, uvicorn" 2>/dev/null; then
        echo "检测到新版本依赖，正在为您自动升级..."
        if command -v zenity >/dev/null 2>&1; then
            (
                echo "10"; echo "# 正在自动升级依赖包..."
                pip install -r "$APP_DIR/requirements.txt"
                echo "100"; echo "# 升级完成！"
            ) | zenity --progress --title="火花助手环境升级" --text="准备升级..." --percentage=0 --auto-close --auto-kill
        else
            pip install -r "$APP_DIR/requirements.txt"
        fi
    fi
fi

# 释放文件锁
flock -u 200

# 切换到用户数据目录以保证读写权限
cd "$USER_DATA_DIR" || exit 1

# 启动主程序
python3 "$APP_DIR/gui_gtk.py"

