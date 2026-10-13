@echo off
setlocal
cd /d "%~dp0"
title Windows Auto Clicker

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" auto_clicker_interactive.py
) else (
    echo [INFO] Dependencies are not installed. Run setup.bat first.
    pause
    exit /b 1
)

if errorlevel 1 (
    echo.
    echo [ERROR] The program exited unexpectedly. Review the messages above.
    pause
)
