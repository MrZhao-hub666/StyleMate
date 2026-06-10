@echo off
chcp 65001 >nul
cd /d "%~dp0edge"
echo ================================
echo   StyleMate 边端启动中...
echo   端口: 9001
echo ================================
uv run uvicorn server:app --host 0.0.0.0 --port 9001
pause
