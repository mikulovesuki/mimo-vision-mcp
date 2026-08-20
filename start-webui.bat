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

rem ---------- [1/4] .env ----------
if exist ".env" goto :have_env
copy /y ".env.example" ".env" >nul
echo [1/4] Created .env from .env.example
echo       Please set your API key: edit .env (MIMO_API_KEY)
echo       or simply fill it in the WebUI and click "Apply to CLI".
goto :env_done
:have_env
echo [1/4] .env ready
:env_done

rem ---------- [2/4] venv ----------
if exist "%PY%" goto :have_venv
echo [2/4] First run: creating virtual environment ...
python -m venv .venv 2>nul
if errorlevel 1 py -3 -m venv .venv
if not exist "%PY%" goto :err
:have_venv
echo [2/4] Virtual environment ready

rem ---------- [3/4] dependencies ----------
echo [3/4] Checking dependencies ...
"%PY%" -c "import fastapi, uvicorn, openai, mcp" >nul 2>nul
if not errorlevel 1 goto :have_deps
echo       Installing dependencies (needs network, please wait)...
"%PY%" -m pip install --quiet -e ".[web]"
if errorlevel 1 goto :err
:have_deps
echo       Dependencies ready

rem ---------- [4/4] port check + start ----------
netstat -ano | findstr /r /c:":%PORT% .*LISTENING" >nul 2>nul
if not errorlevel 1 (
    echo [4/4] Service already running, opening browser ...
    start "" "%URL%"
    exit /b 0
)

echo [4/4] Starting service: %URL%
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
