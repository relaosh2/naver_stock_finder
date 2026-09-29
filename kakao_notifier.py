import requests
import json
import time
from datetime import datetime
from scanner import run_stock_scan

# 사용자 등록 카카오 REST API 키
KAKAO_REST_API_KEY = "5bdff8c65268e9e854682507176f7b85"

# 오늘 이미 알림을 보낸 종목 코드 저장 (중복 알림 방지)
alerted_today = set()

def send_kakao_stock_alert(access_token_or_key: str, stock: dict) -> tuple:
    """
    카카오톡 '나에게 보내기' API를 사용하여 바닥 반등 포착 종목 알림 메시지 전송
    반환값: (성공여부: bool, 메세지: str)
    """
    token = access_token_or_key if access_token_or_key else KAKAO_REST_API_KEY
    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {
        "Authorization": f"Bearer {token}",
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
            "title": f"📈 [갓성호님의 바닥에서 난 잡아] 반등 신호 포착!",
            "description": f"📌 {name} ({code})\n• 반등점수: {score}점 [{grade}]\n• 현재가: {price:,}원 (52주최저 대비 +{diff_low:.1f}%)\n• 외인 3일: {f_buy:+,}주 | 기관: {o_buy:+,}주\n\n💡 포착사유:\n• {reasons}",
            "image_url": "https://img.icons8.com/color/192/line-chart.png",
            "link": {
                "web_url": "https://realosh-stock.streamlit.app",
                "mobile_web_url": "https://realosh-stock.streamlit.app"
            }
        },
        "buttons": [
            {
                "title": "📱 모바일 앱에서 차트 보기",
                "link": {
                    "web_url": "https://realosh-stock.streamlit.app",
                    "mobile_web_url": "https://realosh-stock.streamlit.app"
                }
            }
        ]
    }

    payload = {
        "template_object": json.dumps(template)
    }

    try:
        res = requests.post(url, headers=headers, data=payload, timeout=5)
        if res.status_code == 200:
            msg = f"✅ [{name}] 카카오톡 알림 전송 성공!"
            print(msg)
            return True, msg
        elif res.status_code == 401:
            msg = f"🔑 카카오톡 Access Token(로그인 토큰)이 필요합니다.\nREST API 키({token[:6]}***)는 카카오 로그인 토큰이 아니므로 401 오류가 발생합니다."
            print(msg)
            return False, msg
        else:
            msg = f"❌ 카카오톡 전송 실패 ({res.status_code}): {res.text}"
            print(msg)
            return False, msg
    except Exception as e:
        msg = f"❌ 카카오톡 API 에러: {e}"
        print(msg)
        return False, msg


def run_realtime_kakao_scanner(access_token_or_key: str = KAKAO_REST_API_KEY, min_score: int = 70, market: str = "ALL", top_n: int = 150):
    """
    실시간 종목 스캔 수행 후 조건 충족 시 카카오톡 알림 발송
    """
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
            success, _ = send_kakao_stock_alert(access_token_or_key, stock)
            if success:
                alerted_today.add(code)
                sent_count += 1
                time.sleep(1.5)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✨ 스캔 완료 (신규 알림 전송: {sent_count}건)\n")
    return target_stocks


if __name__ == "__main__":
    print(f"카카오톡 알림 모듈 설정 완료! (REST API KEY: {KAKAO_REST_API_KEY[:6]}***)")
