@echo off
chcp 65001 > nul
echo ========================================================
echo  네이버 증권 바닥 반등 유망주 발굴기 데스크톱 앱을 실행합니다.
echo ========================================================
echo.

if exist "dist\StockFinder\StockFinder.exe" (
    echo [독립 실행 파일 실행] dist\StockFinder\StockFinder.exe 구동 중...
    start "" "dist\StockFinder\StockFinder.exe"
) else (
    echo [파이썬 스크립트 실행] desktop_app.py 구동 중...
    python desktop_app.py
)
