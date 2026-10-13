# Windows 交互连点器

一个面向 Windows 的轻量级 Python 连点器。支持交互式设置点击坐标、次数与间隔，并提供多种紧急停止方式。

## 功能

- 交互式采集一个或多个点击坐标
- 可设置循环次数、点击间隔和开始前倒计时
- 按 `Esc` 停止任务
- 将鼠标移到屏幕左上角可触发 PyAutoGUI 紧急停止
- 附带坐标查看工具

## 下载 EXE（推荐）

在 GitHub 项目的 **Releases** 页面下载 `auto-clicker-v1.0.0-windows-x64.zip`，解压后双击 `auto-clicker.exe`。无需安装 Python，运行时会有一个交互式命令行窗口，这是程序界面的一部分。

Windows SmartScreen 或部分杀毒软件可能对未经数字签名的 PyInstaller 程序给出提示。请只从本项目 Releases 下载，并使用同名 `.sha256` 文件核对校验值；有疑虑时可按下文从源码运行或自行构建。

## 从源码运行

- Windows 10/11
- Python 3.10 或更高版本

需要 Windows 10/11 和 Python 3.10 或更高版本。双击 `setup.bat` 安装依赖，然后双击 `run.bat`。

也可以在终端中执行：

```powershell
py -3 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python auto_clicker_interactive.py
```

查看鼠标坐标：

```powershell
.venv\Scripts\python coord_finder.py
```

## 文件说明

- `auto_clicker_interactive.py`：推荐使用的交互式版本
- `auto_clicker.py`：基础脚本版本
- `coord_finder.py`：鼠标坐标查看工具
- `assets/auto_clicker.ico`：构建可执行文件时使用的图标

## 构建 Windows 可执行文件

先运行 `setup.bat`，再双击 `build.bat`。生成结果位于 `dist/auto-clicker.exe`。

脚本同时生成 `dist/auto-clicker-v1.0.0-windows-x64.zip` 和对应的 `.sha256` 校验文件。将 ZIP 和校验文件上传到 GitHub Releases，不要把 `dist/` 提交到源码分支。

## 使用提醒

请仅在你有权控制的软件和设备上使用。本项目不保证适用于游戏、抢购、广告点击或任何违反第三方服务条款的场景。运行前请确认 `Esc` 和鼠标左上角紧急停止功能正常。

## 许可证

[MIT License](LICENSE)
