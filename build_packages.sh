#!/bin/bash
set -e
# 一键打包脚本：生成 .deb 和 .rpm 包

VERSION="1.3.11"
APP_NAME="sparkassistant"
MAINTAINER="Zhaozikai110812 <zhaozikai110812@users.noreply.github.com>"
DESCRIPTION="基于 GTK4 的抖音商业全自动防风控群发与代续系统"

echo "=== 准备清理并构建打包环境 ==="
rm -rf build_deb build_rpm
mkdir -p build_deb/usr/share/sparkassistant
mkdir -p build_deb/usr/bin
mkdir -p build_deb/usr/share/applications
mkdir -p build_deb/DEBIAN

echo "=== 编译 Web 前端 ==="
export PATH=$PWD/node-v22.2.0-linux-x64/bin:$PATH
(cd web_ui && npm install && npm install @rolldown/binding-linux-x64-gnu -f && npm run build)

echo "=== 复制核心代码与资源 ==="
# 复制源文件
cp -r *.py requirements.txt donate.png build_deb/usr/share/sparkassistant/
mkdir -p build_deb/usr/share/sparkassistant/web_ui
cp -r web_ui/dist build_deb/usr/share/sparkassistant/web_ui/
cp sparkassistant.desktop build_deb/usr/share/applications/
cp sparkassistant-launcher.sh build_deb/usr/bin/sparkassistant
chmod +x build_deb/usr/bin/sparkassistant

# --- 添加拦截 bitbrowser:// 协议的虚拟应用 ---
# 解决 Linux 下比特浏览器尝试打开 bitbrowser:// 导致的“无可用应用”弹窗问题
cat <<EOF > build_deb/usr/share/applications/bitbrowser-dummy.desktop
[Desktop Entry]
Name=BitBrowser Protocol Handler
Comment=Silently handles bitbrowser:// links
Exec=/usr/bin/true %u
Terminal=false
Type=Application
MimeType=x-scheme-handler/bitbrowser;
NoDisplay=true
EOF

echo "=== 构建 Debian (.deb) 包 ==="
# 创建 control 文件
cat <<EOF > build_deb/DEBIAN/control
Package: $APP_NAME
Version: $VERSION
Architecture: amd64
Maintainer: $MAINTAINER
Depends: python3, python3-venv, python3-gi, python3-gi-cairo, gir1.2-gtk-4.0, gir1.2-adw-1, libappindicator3-1, gir1.2-ayatanaappindicator3-0.1 | gir1.2-appindicator3-0.1
Description: $DESCRIPTION
EOF

# --- 添加 DEB 安装后脚本 (postinst) ---
cat <<EOF > build_deb/DEBIAN/postinst
#!/bin/bash
set -e
# 更新桌面数据库，使 bitbrowser:// 协议处理生效
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
exit 0
EOF
chmod 755 build_deb/DEBIAN/postinst

# 生成 .deb
dpkg-deb --build build_deb
mv build_deb.deb ${APP_NAME}_${VERSION}_amd64.deb
echo "✅ DEB 打包完成: ${APP_NAME}_${VERSION}_amd64.deb"

echo "=== 构建 RedHat (.rpm) 包 ==="
# 设置 rpmbuild 目录结构
RPM_DIR="$(pwd)/build_rpm"
mkdir -p $RPM_DIR/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

# 将准备好的文件结构打成 tar 供 rpmbuild 使用
tar -czf $RPM_DIR/SOURCES/${APP_NAME}-${VERSION}.tar.gz -C build_deb usr

# 创建 spec 文件
cat <<EOF > $RPM_DIR/SPECS/${APP_NAME}.spec
%define debug_package %{nil}

Name:           $APP_NAME
Version:        $VERSION
Release:        1%{?dist}
Summary:        $DESCRIPTION
License:        MIT
Source0:        %{name}-%{version}.tar.gz
Requires:       python3, python3-gobject, gtk4, libadwaita, libappindicator-gtk3
BuildArch:      noarch

%description
$DESCRIPTION

%prep
%setup -c

%install
rm -rf \$RPM_BUILD_ROOT
mkdir -p \$RPM_BUILD_ROOT
cp -r usr \$RPM_BUILD_ROOT/

%files
/usr/share/sparkassistant/*
/usr/share/applications/sparkassistant.desktop
/usr/share/applications/bitbrowser-dummy.desktop
/usr/bin/sparkassistant

%changelog
* Tue Jul 14 2026 $MAINTAINER - 1.0.0-1
- Initial release
EOF

# 生成 .rpm
rpmbuild --define "_topdir $RPM_DIR" -bb $RPM_DIR/SPECS/${APP_NAME}.spec
find $RPM_DIR/RPMS -name "*.rpm" -exec cp {} . \;
echo "✅ RPM 打包完成！"

echo "=== 准备 fnOS (.fpk) 包资源 ==="
rm -rf build_fnnas/app/*.py build_fnnas/app/requirements.txt build_fnnas/app/web_ui build_fnnas/app/donate.png
cp -r *.py requirements.txt donate.png build_fnnas/app/
mkdir -p build_fnnas/app/web_ui
cp -r web_ui/dist build_fnnas/app/web_ui/

echo "=== 构建 fnOS (.fpk) 包 ==="
if [ -x /tmp/fnpack ]; then
    /tmp/fnpack build --directory build_fnnas
    mv sparkassistant.fpk ${APP_NAME}_${VERSION}_amd64.fpk || true
    echo "✅ FPK 打包完成: ${APP_NAME}_${VERSION}_amd64.fpk"
else
    echo "⚠️ 未找到 /tmp/fnpack，跳过 FPK 打包"
fi

echo "=== 打包流程全部结束！ ==="
ls -l *.deb *.rpm *.fpk
