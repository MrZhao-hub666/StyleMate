@echo off
chcp 65001 >nul
cd /d "%~dp0backend"
echo ================================
echo   StyleMate 后端启动中...
echo   端口: 9000
echo ================================
uv run uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload
pause
