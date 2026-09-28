# Third-party components in the Windows portable build

The application includes unmodified Qt and PySide6 6.11.2 shared libraries.
Their package metadata offers LGPL-3.0-only, GPL-2.0-only or GPL-3.0-only licensing.
The LGPLv3 text and its GPLv3 supplement are included in `licenses/`.
The shared libraries can be replaced in `_internal/PySide6` and `_internal/shiboken6`.
No additional restriction is imposed on modifying these components or reverse engineering
this application for debugging modifications to the LGPL components.

Corresponding upstream source:

- Qt 6.11.2: https://download.qt.io/archive/qt/6.11/6.11.2/single/
- PySide6 / Shiboken6: https://code.qt.io/cgit/pyside/pyside-setup.git/ (tag v6.11.2)
- Build instructions: https://doc.qt.io/qtforpython-6/building_from_source/index.html

Playwright 1.63.0 is licensed under Apache-2.0. Chromium and its dependencies
have their own notices in `_internal/browsers/` and Playwright's driver directory.
Python's license is shipped with the embedded runtime. Package metadata and
available upstream notices for PySide6, Shiboken6, Playwright, greenlet and pyee
are in the corresponding `_internal/*.dist-info/` directories.

Project source and Windows build scripts:
https://github.com/xuezhangjam/DouyinSparkAssistant
