@echo off
chcp 65001 > nul
echo ========================================================
echo  네이버 증권 바닥 반등 유망주 발굴기 .exe 앱 빌드를 시작합니다.
echo ========================================================
echo.

echo [1/2] 의존성 라이브러리 검증 및 설치 중...
pip install -r requirements.txt

echo.
echo [2/2] PyInstaller를 통해 독립 실행형 .exe 파일 패키징 중...
pyinstaller --noconfirm --onedir --windowed --name StockFinder --collect-all customtkinter --hidden-import pandas --hidden-import numpy --hidden-import FinanceDataReader --hidden-import plotly desktop_app.py

echo.
echo ========================================================
echo  빌드 완료!
echo  생성된 실행 파일 위치: dist\StockFinder\StockFinder.exe
echo ========================================================
echo  dist\StockFinder 폴더 전체를 복사/압축하여 다른 PC에서 실행하시면 됩니다.
echo.
pause
