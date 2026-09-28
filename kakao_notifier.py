import requests
import json
import time
from datetime import datetime
from scanner import run_stock_scan

# 오늘 이미 알림을 보낸 종목 코드 저장 (중복 알림 방지)
alerted_today = set()

def send_kakao_stock_alert(access_token: str, stock: dict) -> bool:
    """
    카카오톡 '나에게 보내기' API를 사용하여 바닥 반등 포착 종목 알림 메시지 전송
    """
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
            "title": f"📈 [갓성호님의 바닥에서 난 잡아] 반등 신호 포착!",
            "description": f"📌 {name} ({code})\n• 반등점수: {score}점 [{grade}]\n• 현재가: {price:,}원 (52주최저 대비 +{diff_low:.1f}%)\n• 외인 3일: {f_buy:+,}주 | 기관: {o_buy:+,}주\n\n💡 포착사유:\n• {reasons}",
            "image_url": "https://img.icons8.com/color/192,line-chart.png",
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
        res = requests.post(url, headers=headers, data=payload)
        if res.status_code == 200:
            print(f"✅ [{name}] 카카오톡 알림 전송 성공!")
            return True
        else:
            print(f"❌ 카카오톡 전송 실패 ({res.status_code}): {res.text}")
            return False
    except Exception as e:
        print(f"❌ 카카오톡 API 에러: {e}")
        return False


def run_realtime_kakao_scanner(access_token: str, min_score: int = 70, market: str = "ALL", top_n: int = 150):
    """
    실시간 종목 스캔 수행 후 조건 충족 시 카카오톡 알림 발송
    """
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 카카오톡 실시간 바닥 반등 종목 스캔 시작...")
    df_res = run_stock_scan(market=market, top_n=top_n)

    if df_res is None or df_res.empty:
        print("발굴된 종목이 없습니다.")
        return []

    # 점수 조건 및 오늘 미발송 종목 필터링
    target_stocks = df_res[df_res['total_score'] >= min_score].to_dict('records')
    sent_count = 0

    for stock in target_stocks:
        code = stock['code']
        if code not in alerted_today:
            success = send_kakao_stock_alert(access_token, stock)
            if success:
                alerted_today.add(code)
                sent_count += 1
                time.sleep(1) # 카카오 API 도배 방지 1초 대기

    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✨ 스캔 완료 (신규 알림 전송: {sent_count}건)\n")
    return target_stocks


if __name__ == "__main__":
    # 카카오 Access Token 테스트 샘플
    TEST_TOKEN = "YOUR_KAKAO_ACCESS_TOKEN"
    print("카카오톡 알림 모듈이 성공적으로 로드되었습니다.")
