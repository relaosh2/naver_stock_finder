# 📱 PC 없이 스마트폰 5G/LTE 24시간 전용 모바일 앱 배포 가이드

PC를 켜놓지 않고도 **스마트폰 5G / LTE 자체 인터넷으로 24시간 언제 어디서나 접속하여 사용할 수 있는 무료 모바일 앱 구축 방법**입니다.

---

## ⚡ 1단계: GitHub에 코드 올리기 (1분 소요)

1. [GitHub 공식 사이트 (github.com)](https://github.com) 로그인 후 우측 상단 **[+ -> New repository]** 클릭.
2. Repository name에 `naver_stock_finder` 입력 후 **[Create repository]** 클릭.
3. 내 PC의 명령 프롬프트(CMD) 창을 열고, 아래 두 줄을 순서대로 복사하여 실행합니다:
   ```cmd
   git remote add origin https://github.com/본인GitHub아이디/naver_stock_finder.git
   git push -u origin master
   ```

---

## 🚀 2단계: Streamlit Cloud 24시간 1-Click 배포 (1분 소요)

1. [Streamlit Community Cloud (share.streamlit.io)](https://share.streamlit.io) 접속 후 GitHub 계정으로 로그인.
2. 우측 상단 **[New app]** 버튼 클릭 후 아래 정보 입력:
   - **Repository**: `본인GitHub아이디/naver_stock_finder`
   - **Branch**: `master`
   - **Main file path**: `mobile_app.py`
3. **[Deploy!]** 버튼 클릭!
4. 약 1분 후 나만의 **24시간 전용 모바일 앱 주소 (예: `https://my-stock-finder.streamlit.app`)**가 자동으로 생성됩니다.

---

## 📱 3단계: 스마트폰 5G / LTE 홈 화면 앱 등록

1. 스마트폰(Android 또는 iPhone) 5G/LTE 인터넷 환경에서 발급받은 주소로 접속합니다.
2. **Android (Chrome)**:
   - 우측 상단 `[⋮]` 메뉴 클릭 -> **[홈 화면에 추가]** 또는 **[앱 설치]** 선택
3. **iPhone (Safari)**:
   - 하단 중앙 `[공유]` 아이콘 클릭 -> **[홈 화면에 추가]** 선택
4. 스마트폰 바탕화면에 생성된 **'주식찾기'** 앱 아이콘을 터치하면 PC가 꺼져 있어도 24시간 언제든 5G/LTE 모바일 자체 인터넷으로 사용할 수 있습니다!
