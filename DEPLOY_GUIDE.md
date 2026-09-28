# 🌐 24시간 스마트폰 모바일 앱 100% 무료 배포 가이드 (Streamlit Cloud)

컴퓨터(PC)를 켜놓지 않고도 **스마트폰에서 24시간 언제 어디서나 접속할 수 있는 모바일 전용 주식찾기 앱** 무료 배포 방법입니다.

---

## 🚀 1. GitHub에 소스코드 올리기 (초간단 3분)

1. [GitHub 공식 사이트](https://github.com)에 로그인 후 **[New Repository]**를 눌러 새 저장소를 생성합니다.
   - Repository Name: `naver_stock_finder`
2. 생성된 저장소에 아래 파일들을 업로드합니다:
   - `mobile_app.py`
   - `data_fetcher.py`
   - `scanner.py`
   - `technical_indicators.py`
   - `rebound_scorer.py`
   - `requirements.txt`

---

## ⚡ 2. Streamlit Cloud에 1-Click 무료 배포하기

1. [Streamlit Community Cloud](https://streamlit.io/cloud) 사이트에 접속하여 GitHub 계정으로 로그인합니다.
2. 우측 상단 **[New app]** 버튼을 클릭합니다.
3. 설정값을 입력합니다:
   - **Repository**: `본인ID/naver_stock_finder`
   - **Branch**: `main`
   - **Main file path**: `mobile_app.py`
4. **[Deploy!]** 버튼을 누르면 약 1분 후 나만의 **무료 모바일 앱 웹 주소 (예: `https://my-stock-finder.streamlit.app`)**가 생성됩니다!

---

## 📱 3. 스마트폰(Android / iPhone) 홈 화면에 앱으로 설치하기

1. 스마트폰에서 생성된 링크(`https://my-stock-finder.streamlit.app`)로 접속합니다.
2. **Android (Chrome)**:
   - 우측 상단 `[⋮]` 메뉴 버튼 클릭 → **[홈 화면에 추가]** 또는 **[앱 설치]** 선택
3. **iPhone (Safari)**:
   - 하단 중앙 `[공유]` 버튼 클릭 → **[홈 화면에 추가]** 선택
4. 스마트폰 바탕화면에 **'주식찾기'** 앱 아이콘이 생성되어 터치 한 번으로 모바일 전용 앱으로 바로 실행됩니다!
