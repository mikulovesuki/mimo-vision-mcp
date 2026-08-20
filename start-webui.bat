@echo off
setlocal
cd /d "%~dp0"
title mimo-vision WebUI Launcher

set "PY=.venv\Scripts\python.exe"
set "URL=http://127.0.0.1:8000"
set "PORT=8000"

echo ============================================
echo   mimo-vision Vision Model WebUI - Launcher
echo ============================================
echo.

rem ---------- [1/3] venv ----------
if exist "%PY%" goto :have_venv
echo [1/3] First run: creating virtual environment ...
python -m venv .venv 2>nul
if errorlevel 1 py -3 -m venv .venv
if not exist "%PY%" goto :err
:have_venv
echo [1/3] Virtual environment ready

rem ---------- [2/3] dependencies ----------
echo [2/3] Checking dependencies ...
"%PY%" -c "import fastapi, uvicorn, openai, mcp" >nul 2>nul
if not errorlevel 1 goto :have_deps
echo       Installing dependencies (needs network, please wait)...
"%PY%" -m pip install --quiet -e ".[web]"
if errorlevel 1 goto :err
:have_deps
echo       Dependencies ready

rem ---------- [3/3] port check + start ----------
netstat -ano | findstr /r /c:":%PORT% .*LISTENING" >nul 2>nul
if not errorlevel 1 (
    echo [3/3] Service already running, opening browser ...
    start "" "%URL%"
    exit /b 0
)

echo [3/3] Starting service: %URL%
echo       Press Ctrl+C to stop.
echo.

rem Open the browser automatically after 3 seconds.
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 3; Start-Process '%URL%'"

"%PY%" -m webui.app
exit /b 0

:err
echo.
echo [ERROR] Failed to start. Please check the messages above.
echo         Common causes: no network / Python not installed / port in use
pause
