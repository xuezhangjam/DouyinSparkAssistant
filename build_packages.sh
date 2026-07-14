#!/bin/bash
# 一键打包脚本：生成 .deb 和 .rpm 包

VERSION="1.0.2"
APP_NAME="sparkassistant"
MAINTAINER="Zhaozikai110812 <zhaozikai110812@users.noreply.github.com>"
DESCRIPTION="基于 GTK4 的抖音商业全自动防风控群发与代续系统"

echo "=== 准备清理并构建打包环境 ==="
rm -rf build_deb build_rpm
mkdir -p build_deb/usr/share/sparkassistant
mkdir -p build_deb/usr/bin
mkdir -p build_deb/usr/share/applications
mkdir -p build_deb/DEBIAN

echo "=== 复制核心代码与资源 ==="
# 复制源文件
cp -r *.py requirements.txt build_deb/usr/share/sparkassistant/
cp sparkassistant.desktop build_deb/usr/share/applications/
cp sparkassistant-launcher.sh build_deb/usr/bin/sparkassistant
chmod +x build_deb/usr/bin/sparkassistant

echo "=== 构建 Debian (.deb) 包 ==="
# 创建 control 文件
cat <<EOF > build_deb/DEBIAN/control
Package: $APP_NAME
Version: $VERSION
Architecture: amd64
Maintainer: $MAINTAINER
Depends: python3, python3-venv, python3-gi, python3-gi-cairo, gir1.2-gtk-4.0, gir1.2-adw-1, libappindicator3-1
Description: $DESCRIPTION
EOF

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
Requires:       python3, python3-gobject, gtk4, libadwaita
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
/usr/bin/sparkassistant

%changelog
* Tue Jul 14 2026 $MAINTAINER - 1.0.0-1
- Initial release
EOF

# 生成 .rpm
rpmbuild --define "_topdir $RPM_DIR" -bb $RPM_DIR/SPECS/${APP_NAME}.spec
find $RPM_DIR/RPMS -name "*.rpm" -exec cp {} . \;
echo "✅ RPM 打包完成！"

echo "=== 打包流程全部结束！ ==="
ls -l *.deb *.rpm
