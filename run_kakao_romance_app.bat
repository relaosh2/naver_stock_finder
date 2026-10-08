@echo off
chcp 65001 > nul
echo =========================================================
echo 💘 카카오톡 썸^&연애 호감도 분석기 (독립 실행)
echo =========================================================
echo.
echo 웹 브라우저에서 별도 주소(포트 8502)로 실행합니다...
echo 주소: http://localhost:8502
echo.
streamlit run kakao_romance_analyzer.py --server.port 8502
pause
