%define debug_package %{nil}

Name:           sparkassistant
Version:        1.2.4
Release:        1%{?dist}
Summary:        基于 GTK4 的抖音商业全自动防风控群发与代续系统
License:        MIT
Source0:        %{name}-%{version}.tar.gz
Requires:       python3, python3-gobject, gtk4, libadwaita
BuildArch:      noarch

%description
基于 GTK4 的抖音商业全自动防风控群发与代续系统

%prep
%setup -c

%install
rm -rf $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT
cp -r usr $RPM_BUILD_ROOT/

%files
/usr/share/sparkassistant/*
/usr/share/applications/sparkassistant.desktop
/usr/bin/sparkassistant

%changelog
* Tue Jul 14 2026 Zhaozikai110812 <zhaozikai110812@users.noreply.github.com> - 1.0.0-1
- Initial release
