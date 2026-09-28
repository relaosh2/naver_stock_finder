@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo ========================================================
echo  네이버 증권 바닥 반등 주식찾기 모바일 앱 서버 구동중...
echo ========================================================
echo.

python qrcode_gen.py

echo 모바일 앱 서버를 가동합니다 (Flask Port 5000)...
echo.

python mobile_server.py

pause
