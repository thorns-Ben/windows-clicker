@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Run setup.bat first.
    pause
    exit /b 1
)

echo Installing build tools...
".venv\Scripts\python.exe" -m pip install -r requirements-dev.txt
if errorlevel 1 goto :failed

echo Building executable and GitHub Releases ZIP...
".venv\Scripts\python.exe" build_release.py
if errorlevel 1 goto :failed

echo.
echo Build completed. See dist\ for the EXE, ZIP and SHA-256 file.
pause
exit /b 0

:failed
echo.
echo [ERROR] Build failed. Review the messages above.
pause
exit /b 1
