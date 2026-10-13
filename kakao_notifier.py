import os
import requests
import json
import time
from datetime import datetime
from scanner import run_stock_scan

# 사용자 등록 카카오 REST API 키 및 주소
DEFAULT_KAKAO_KEY = "5bdff8c65268e9e854682507176f7b85"
DEFAULT_CLIENT_SECRET = "CExMxLRJ6NrDW6gPG5mhHKROiwtuIM34"
DEFAULT_REDIRECT_URI = "https://realoshstock2.streamlit.app"


KAKAO_TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kakao_tokens.json")

try:
    import streamlit as st
    KAKAO_REST_API_KEY = st.secrets.get("KAKAO_REST_API_KEY", DEFAULT_KAKAO_KEY)
    KAKAO_CLIENT_SECRET = st.secrets.get("KAKAO_CLIENT_SECRET", DEFAULT_CLIENT_SECRET)
except Exception:
    KAKAO_REST_API_KEY = DEFAULT_KAKAO_KEY
    KAKAO_CLIENT_SECRET = DEFAULT_CLIENT_SECRET

REDIRECT_URI = DEFAULT_REDIRECT_URI


def save_kakao_tokens(tokens: dict):
    """발급받은 카카오 토큰(access_token, refresh_token)을 파일에 영구 저장"""
    try:
        existing = {}
        if os.path.exists(KAKAO_TOKEN_FILE):
            with open(KAKAO_TOKEN_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f)
        existing.update(tokens)
        existing["updated_at"] = datetime.now().isoformat()
        with open(KAKAO_TOKEN_FILE, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def load_saved_kakao_token() -> str:
    """저장된 카카오 Access Token 로드 (만료 시 Refresh Token으로 자동 갱신 시도)"""
    if not os.path.exists(KAKAO_TOKEN_FILE):
        return ""
    try:
        with open(KAKAO_TOKEN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("access_token", "")
    except Exception:
        return ""


def get_redirect_uri() -> str:
    """
    현재 접속한 Streamlit 앱의 도메인(URI)을 동적으로 감지하거나 기본값 반환
    """
    try:
        import streamlit as st
        if hasattr(st, "context") and hasattr(st.context, "headers"):
            headers = st.context.headers
            host = headers.get("host") or headers.get("Host") or headers.get("x-forwarded-host")
            if host:
                proto = headers.get("x-forwarded-proto", "https")
                return f"{proto}://{host}".rstrip("/")
    except Exception:
        pass

    try:
        import streamlit as st
        if "REDIRECT_URI" in st.secrets:
            return st.secrets["REDIRECT_URI"].rstrip("/")
    except Exception:
        pass

    return DEFAULT_REDIRECT_URI.rstrip("/")


# 오늘 이미 알림을 보낸 종목 코드 저장 (중복 알림 방지)
alerted_today = set()


def exchange_code_for_tokens(auth_code: str, redirect_uri: str = None) -> dict:
    """
    카카오 인가 코드(code)를 Access Token & Refresh Token으로 교환
    """
    if not redirect_uri:
        redirect_uri = get_redirect_uri()
    url = "https://kauth.kakao.com/oauth/token"

    # 슬래시 유무에 따른 호환성을 위해 순차 시도
    base_uri = redirect_uri.rstrip("/")
    candidates = [redirect_uri, base_uri, base_uri + "/"]
    seen = []
    for c in candidates:
        if c not in seen:
            seen.append(c)

    last_err = ""
    for uri_candidate in seen:
        data = {
            "grant_type": "authorization_code",
            "client_id": KAKAO_REST_API_KEY,
            "client_secret": KAKAO_CLIENT_SECRET,
            "redirect_uri": uri_candidate,
            "code": auth_code
        }
        try:
            res = requests.post(url, data=data, timeout=5)
            if res.status_code == 200:
                token_data = res.json()
                if token_data.get("access_token"):
                    save_kakao_tokens(token_data)
                return token_data
            else:
                last_err = f"({res.status_code}) {res.text}"
                if "KOE303" not in res.text:
                    break
        except Exception as e:
            last_err = str(e)
            break

    print(f"❌ 카카오 토큰 교환 실패: {last_err}")
    return {"error": last_err}


def refresh_access_token(refresh_token: str = None) -> str:
    """
    Refresh Token을 사용하여 새 Access Token 갱신
    """
    if not refresh_token and os.path.exists(KAKAO_TOKEN_FILE):
        try:
            with open(KAKAO_TOKEN_FILE, "r", encoding="utf-8") as f:
                refresh_token = json.load(f).get("refresh_token", "")
        except Exception:
            pass
    if not refresh_token:
        return ""

    url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": KAKAO_REST_API_KEY,
        "client_secret": KAKAO_CLIENT_SECRET,
        "refresh_token": refresh_token
    }
    try:
        res = requests.post(url, data=data, timeout=5)
        if res.status_code == 200:
            token_data = res.json()
            new_token = token_data.get("access_token", "")
            if new_token:
                save_kakao_tokens(token_data)
            return new_token
        return ""
    except Exception:
        return ""



def send_kakao_stock_alert(access_token: str, stock: dict) -> tuple:
    """
    카카오톡 '나에게 보내기' API를 사용하여 바닥 반등 포착 종목 알림 메시지 전송
    반환값: (성공여부: bool, 메세지: str)
    """
    if not access_token or access_token == KAKAO_REST_API_KEY:
        saved = load_saved_kakao_token()
        if saved:
            access_token = saved

    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    code = stock['code']
    name = stock['name']
    score = stock['total_score']
    price = stock['current_price']
    diff_low = stock['diff_from_52w_low_pct']
    f_buy = stock['foreign_buy_3d']
    o_buy = stock['organ_buy_3d']
    grade = stock['grade']
    reasons = "\n• ".join(stock['reasons'][:3])

    # 카카오톡 메시지 템플릿
    template = {
        "object_type": "feed",
        "content": {
            "title": "📈 [갓성호님의 바닥에서 난 잡아] 반등 신호 포착!",
            "description": f"📌 {name} ({code})\n• 반등점수: {score}점 [{grade}]\n• 현재가: {price:,}원 (52주최저 대비 +{diff_low:.1f}%)\n• 외인 3일: {f_buy:+,}주 | 기관: {o_buy:+,}주\n\n💡 포착사유:\n• {reasons}",
            "image_url": "https://img.icons8.com/color/192/line-chart.png",
            "link": {
                "web_url": REDIRECT_URI,
                "mobile_web_url": REDIRECT_URI
            }
        },
        "buttons": [
            {
                "title": "📱 모바일 앱에서 차트 보기",
                "link": {
                    "web_url": REDIRECT_URI,
                    "mobile_web_url": REDIRECT_URI
                }
            }
        ]
    }

    payload = {
        "template_object": json.dumps(template)
    }

    try:
        res = requests.post(url, headers=headers, data=payload, timeout=5)
        if res.status_code == 401:
            # 토큰 만료 시 자동 리프레시 시도
            refreshed = refresh_access_token()
            if refreshed:
                headers["Authorization"] = f"Bearer {refreshed}"
                res = requests.post(url, headers=headers, data=payload, timeout=5)

        if res.status_code == 200:
            msg = f"✅ [{name}] 카카오톡 알림 전송 성공!"
            print(msg)
            return True, msg
        elif res.status_code == 401:
            msg = "🔑 카카오톡 연동이 필요합니다. 상단의 [💬 카카오톡 1초 로그인 연동하기] 버튼을 터치해주세요."
            print(msg)
            return False, msg
        else:
            msg = f"❌ 카카오톡 전송 결과 ({res.status_code}): {res.text}"
            print(msg)
            return False, msg
    except Exception as e:
        msg = f"❌ 카카오톡 API 에러: {e}"
        print(msg)
        return False, msg


def run_realtime_kakao_scanner(access_token: str, min_score: int = 70, market: str = "ALL", top_n: int = 150):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 카카오톡 실시간 바닥 반등 종목 스캔 시작...")
    df_res = run_stock_scan(market=market, top_n=top_n)

    if df_res is None or df_res.empty:
        print("발굴된 종목이 없습니다.")
        return []

    target_stocks = df_res[df_res['total_score'] >= min_score].to_dict('records')
    sent_count = 0

    for stock in target_stocks:
        code = stock['code']
        if code not in alerted_today:
            success, _ = send_kakao_stock_alert(access_token, stock)
            if success:
                alerted_today.add(code)
                sent_count += 1
                time.sleep(1.5)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✨ 스캔 완료 (신규 알림 전송: {sent_count}건)\n")
    return target_stocks
